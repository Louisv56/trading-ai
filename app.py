from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import os
import json
import hashlib
import stripe
import threading
import time
import urllib.request
import urllib.parse
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
from supabase import create_client, Client
from datetime import date

# ── Clients ──────────────────────────────────────────────────────────────────
openai_client    = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

stripe.api_key  = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_PREMIUM   = os.getenv("STRIPE_PRICE_PREMIUM")
PRICE_PRO       = os.getenv("STRIPE_PRICE_PRO")
FRONTEND_URL    = os.getenv("FRONTEND_URL", "https://votre-site.com")

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL  = "https://www.googleapis.com/oauth2/v2/userinfo"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "https://mytradingx.fr",
    "https://www.mytradingx.fr",
    "http://localhost",
    "http://127.0.0.1"
]}}, supports_credentials=True)

@app.after_request
def after_request(response):
    origin = request.headers.get("Origin", "")
    if origin in ["https://mytradingx.fr", "https://www.mytradingx.fr"]:
        response.headers["Access-Control-Allow-Origin"]  = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

# ── Modeles autorises par plan ────────────────────────────────────────────────
MODELS_BY_PLAN = {
    "free":    ["gpt-4o-mini"],
    "premium": ["gpt-4o-mini", "gpt-4o", "gemini"],
    "pro":     ["gpt-4o-mini", "gpt-4o", "gemini", "claude"]
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_auth(email: str, password: str):
    """Retourne l'utilisateur si auth valide (email+password OU Google), sinon None."""
    user = get_user(email)
    if not user:
        return None
    # Cas 1 : mot de passe classique hashé
    if user["password"] == hash_password(password):
        return user
    # Cas 2 : Google Auth — le frontend envoie déjà "GOOGLE_OAUTH_xxxx" en clair
    # Le backend l'a stocké hashé, donc on compare hash(password_reçu) avec ce qui est en base
    if password.startswith("GOOGLE_OAUTH_") and user["password"] == hash_password(password):
        return user
    # Cas 3 : recalcul du hash Google à partir de l'email (compatibilité)
    google_pwd   = "GOOGLE_OAUTH_" + hashlib.sha256(email.encode()).hexdigest()[:16]
    google_hash  = hash_password(google_pwd)
    if user["password"] == google_hash:
        return user
    return None

def get_user(email: str):
    res = supabase.table("users").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None

def reset_counter_if_needed(user: dict):
    today = date.today()
    reset_date = date.fromisoformat(str(user["analyses_reset_date"]))
    if today.month != reset_date.month or today.year != reset_date.year:
        supabase.table("users").update({
            "analyses_utilisees": 0,
            "analyses_reset_date": today.isoformat()
        }).eq("id", user["id"]).execute()
        user["analyses_utilisees"] = 0
    return user

def build_prompt(asset, timeframe):
    return (
        "Tu es un trader professionnel specialise en analyse technique Smart Money Concepts (SMC).\n\n"
        "CONTEXTE :\n"
        "- Actif : " + asset + "\n"
        "- Timeframe principal : " + timeframe + "\n\n"
        "METHODOLOGIE :\n"
        "- Structure de marche : Higher High/Higher Low ou Lower High/Lower Low\n"
        "- Zones institutionnelles : Order Blocks, Fair Value Gaps (FVG), Breaker Blocks\n"
        "- Liquidite : Equal Highs/Lows, BSL/SSL\n"
        "- Flux d ordres : BOS (Break of Structure), CHOCH (Change of Character)\n"
        "- Si deux graphiques fournis : analyse multi-timeframe HTF + LTF\n\n"
        "Reponds UNIQUEMENT avec un JSON valide, sans texte avant ni apres :\n\n"
        "{\n"
        "  \"direction\": \"BUY ou SELL ou NEUTRE\",\n"
        "  \"entrees\": [\"niveau 1\", \"niveau 2\"],\n"
        "  \"stop_loss\": \"niveau avec justification courte\",\n"
        "  \"take_profit\": [\"TP1\", \"TP2\", \"TP3\"],\n"
        "  \"ratio_risque_rendement\": \"ex: 1:3\",\n"
        "  \"confluences\": [\"confluence 1\", \"confluence 2\", \"confluence 3\"],\n"
        "  \"invalidation\": \"condition qui invalide le setup\",\n"
        "  \"probabilite_succes\": 72,\n"
        "  \"explication\": \"Analyse detaillee en francais. Ceci n est pas un conseil financier.\"\n"
        "}\n\n"
        "Pour probabilite_succes : entier entre 0 et 100. "
        "Setup moyen = 50-60%, bon = 65-75%, excellent = 75-85%. "
        "Ne depasse jamais 85%."
    )

def clean_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

def get_mime_type(img_bytes):
    if img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif img_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    elif img_bytes[:4] == b'RIFF' and img_bytes[8:12] == b'WEBP':
        return "image/webp"
    else:
        return "image/png"

def call_openai(model_id, prompt, images):
    messages_content = [{"type": "text", "text": prompt}]
    for img_bytes in images:
        mime = get_mime_type(img_bytes)
        messages_content.append({
            "type": "image_url",
            "image_url": {"url": "data:" + mime + ";base64," + base64.b64encode(img_bytes).decode()}
        })
    response = openai_client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": messages_content}],
        max_tokens=1200
    )
    return clean_json(response.choices[0].message.content)

def call_claude(prompt, images):
    content = []
    for img_bytes in images:
        mime = get_mime_type(img_bytes)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": base64.b64encode(img_bytes).decode()
            }
        })
    content.append({"type": "text", "text": prompt})
    response = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": content}]
    )
    return clean_json(response.content[0].text)

def call_gemini(prompt, images):
    model = genai.GenerativeModel("gemini-2.5-flash")
    parts = []
    for img_bytes in images:
        mime = get_mime_type(img_bytes)
        parts.append({
            "mime_type": mime,
            "data": base64.b64encode(img_bytes).decode()
        })
    parts.append(prompt)
    response = model.generate_content(parts)
    return clean_json(response.text)

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS": return "", 204
    try:
        data     = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        if get_user(email):
            return jsonify({"error": "Email deja utilise"}), 400
        supabase.table("users").insert({
            "email": email,
            "password": hash_password(password),
            "plan": "free",
            "analyses_utilisees": 0,
            "analyses_reset_date": date.today().isoformat()
        }).execute()
        user = get_user(email)
        return jsonify({
            "message": "Inscription reussie",
            "user": {"id": user["id"], "email": user["email"], "plan": user["plan"], "analyses_utilisees": user["analyses_utilisees"]}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS": return "", 204
    try:
        data     = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")
        user = get_user(email)
        if not user or user["password"] != hash_password(password):
            return jsonify({"error": "Identifiants incorrects"}), 401
        user = reset_counter_if_needed(user)
        if user["plan"] == "free":
            restantes = max(0, 2 - user["analyses_utilisees"])
        elif user["plan"] == "premium":
            restantes = max(0, 50 - user["analyses_utilisees"])
        else:
            restantes = 999
        return jsonify({
            "message": "Connexion reussie",
            "user": {
                "id": user["id"], "email": user["email"], "plan": user["plan"],
                "analyses_utilisees": user["analyses_utilisees"], "analyses_restantes": restantes,
                "modeles_disponibles": MODELS_BY_PLAN.get(user["plan"], ["gpt-4o-mini"])
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Google OAuth ─────────────────────────────────────────────────────────────
@app.route("/auth/google/callback", methods=["POST", "OPTIONS"])
def google_callback():
    if request.method == "OPTIONS":
        return "", 204
    try:
        data = request.get_json()
        code         = data.get("code", "")
        redirect_uri = data.get("redirect_uri", FRONTEND_URL + "/login.html")
        if not code:
            return jsonify({"error": "Code manquant"}), 400

        # 1. Echanger le code contre un access_token
        token_data = urllib.parse.urlencode({
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code"
        }).encode()

        token_req = urllib.request.Request(
            GOOGLE_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token_resp = urllib.request.urlopen(token_req)
        token_json = json.loads(token_resp.read().decode())
        access_token = token_json.get("access_token")
        if not access_token:
            return jsonify({"error": "Token Google invalide"}), 400

        # 2. Recuperer les infos utilisateur Google
        info_req  = urllib.request.Request(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": "Bearer " + access_token}
        )
        info_resp = urllib.request.urlopen(info_req)
        info      = json.loads(info_resp.read().decode())
        email     = info.get("email", "").strip().lower()
        if not email:
            return jsonify({"error": "Email Google introuvable"}), 400

        # 3. Creer ou recuperer l'utilisateur
        user = get_user(email)
        if not user:
            # Inscription automatique via Google
            google_password = "GOOGLE_OAUTH_" + hashlib.sha256(email.encode()).hexdigest()[:16]
            supabase.table("users").insert({
                "email":                email,
                "password":             hash_password(google_password),
                "plan":                 "free",
                "analyses_utilisees":   0,
                "analyses_reset_date":  date.today().isoformat()
            }).execute()
            user = get_user(email)

        user = reset_counter_if_needed(user)

        if user["plan"] == "free":
            restantes = max(0, 2 - user["analyses_utilisees"])
        elif user["plan"] == "premium":
            restantes = max(0, 50 - user["analyses_utilisees"])
        else:
            restantes = 999

        return jsonify({
            "message": "Connexion Google reussie",
            "user": {
                "id":                  user["id"],
                "email":               user["email"],
                "plan":                user["plan"],
                "analyses_utilisees":  user["analyses_utilisees"],
                "analyses_restantes":  restantes,
                "modeles_disponibles": MODELS_BY_PLAN.get(user["plan"], ["gpt-4o-mini"]),
                "google_auth":         True
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Analyse ───────────────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze():
    if request.method == "OPTIONS": return "", 204
    try:
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        model    = request.form.get("model", "gpt-4o-mini")

        user = check_auth(email, password)
        if not user:
            return jsonify({"error": "Non autorise. Connecte-toi."}), 401

        user  = reset_counter_if_needed(user)
        plan  = user["plan"]
        count = user["analyses_utilisees"]

        if plan == "free" and count >= 2:
            return jsonify({"error": "LIMIT_REACHED", "plan": "free"}), 403
        if plan == "premium" and count >= 50:
            return jsonify({"error": "LIMIT_REACHED", "plan": "premium"}), 403

        # Verifie que le modele est autorise pour ce plan
        allowed = MODELS_BY_PLAN.get(plan, ["gpt-4o-mini"])
        if model not in allowed:
            return jsonify({"error": "Modele non disponible pour votre plan"}), 403

        asset     = request.form.get("asset", "non precise")
        timeframe = request.form.get("timeframe", "non precise")
        prompt    = build_prompt(asset, timeframe)

        # Lecture des images
        images = []
        if "image_htf" in request.files and request.files["image_htf"].filename != "":
            images.append(request.files["image_htf"].read())
        if "image_ltf" in request.files and request.files["image_ltf"].filename != "":
            images.append(request.files["image_ltf"].read())

        # Appel au bon modele
        if model == "claude":
            result = call_claude(prompt, images)
        elif model == "gemini":
            result = call_gemini(prompt, images)
        elif model == "gpt-4o":
            result = call_openai("gpt-4o", prompt, images)
        else:
            result = call_openai("gpt-4o-mini", prompt, images)

        # Increment compteur
        supabase.table("users").update({
            "analyses_utilisees": count + 1
        }).eq("id", user["id"]).execute()

        # Quota restant
        if plan == "free":
            result["analyses_restantes"] = max(0, 2 - (count + 1))
        elif plan == "premium":
            result["analyses_restantes"] = max(0, 50 - (count + 1))
        else:
            result["analyses_restantes"] = 999

        result["plan"]   = plan
        result["modele"] = model

        # Pastille probabilite
        score = result.get("probabilite_succes", 0)
        if isinstance(score, (int, float)):
            if score >= 70:
                result["proba_couleur"] = "#22c55e"
                result["proba_label"]   = "Haute probabilite"
            elif score >= 50:
                result["proba_couleur"] = "#f97316"
                result["proba_label"]   = "Probabilite neutre"
            else:
                result["proba_couleur"] = "#ef4444"
                result["proba_label"]   = "Faible probabilite"

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Cancel Subscription ───────────────────────────────────────────────────────
@app.route("/cancel-subscription", methods=["POST", "OPTIONS"])
def cancel_subscription():
    if request.method == "OPTIONS": return "", 204
    try:
        data     = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")
        user = check_auth(email, password)
        if not user:
            return jsonify({"error": "Non autorise. Connecte-toi."}), 401
        sub_id = user.get("stripe_subscription_id")
        if not sub_id:
            return jsonify({"error": "Aucun abonnement actif trouve"}), 400
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        return jsonify({"message": "Resiliation confirmee. Votre acces reste actif jusqu a la fin de la periode en cours."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stripe Checkout ───────────────────────────────────────────────────────────
@app.route("/create-checkout", methods=["POST", "OPTIONS"])
def create_checkout():
    if request.method == "OPTIONS": return "", 204
    try:
        data  = request.get_json()
        email = data.get("email", "").strip().lower()
        plan  = data.get("plan")
        if plan not in ["premium", "pro"]:
            return jsonify({"error": "Plan invalide"}), 400
        price_id = PRICE_PREMIUM if plan == "premium" else PRICE_PRO
        user = get_user(email)
        if user and user.get("stripe_customer_id"):
            customer_id = user["stripe_customer_id"]
        else:
            customer = stripe.Customer.create(email=email)
            customer_id = customer.id
            if user:
                supabase.table("users").update({"stripe_customer_id": customer_id}).eq("id", user["id"]).execute()
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=FRONTEND_URL + "?payment=success&plan=" + plan,
            cancel_url=FRONTEND_URL + "?payment=cancelled",
            metadata={"email": email, "plan": plan}
        )
        return jsonify({"url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stripe Webhook ────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST", "OPTIONS"])
def webhook():
    payload = request.data
    sig     = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email   = session["metadata"]["email"]
        plan    = session["metadata"]["plan"]
        sub_id  = session.get("subscription")
        supabase.table("users").update({
            "plan": plan, "analyses_utilisees": 0,
            "analyses_reset_date": date.today().isoformat(),
            "stripe_subscription_id": sub_id
        }).eq("email", email).execute()
    elif event["type"] == "customer.subscription.deleted":
        sub_id = event["data"]["object"]["id"]
        res = supabase.table("users").select("*").eq("stripe_subscription_id", sub_id).execute()
        if res.data:
            supabase.table("users").update({"plan": "free", "analyses_utilisees": 0}).eq("stripe_subscription_id", sub_id).execute()
    return jsonify({"status": "ok"})



# ── Analyse Fondamentale (Pro uniquement) ─────────────────────────────────────
@app.route("/fundamental", methods=["POST", "OPTIONS"])
def fundamental():
    if request.method == "OPTIONS": return "", 204
    try:
        import requests as req

        data     = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")
        asset    = data.get("asset", "").strip()

        if not asset:
            return jsonify({"error": "Precise un actif (ex: BTC, EURUSD, Gold)"}), 400

        user = check_auth(email, password)
        if not user:
            return jsonify({"error": "Non autorise. Connecte-toi."}), 401

        if user["plan"] != "pro":
            return jsonify({"error": "PRO_ONLY"}), 403

        FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

        keywords = [asset.lower(), asset.upper()]
        extra_kw = {
            "BTC": ["bitcoin", "crypto", "btc"],
            "ETH": ["ethereum", "eth", "crypto"],
            "GOLD": ["gold", "xau", "metaux"],
            "EURUSD": ["euro", "eur", "usd", "dollar", "fed", "bce"],
            "SP500": ["sp500", "s&p", "wall street", "fed"],
            "OIL": ["oil", "petrole", "opec", "brent", "wti"],
        }
        for k, v in extra_kw.items():
            if asset.upper() == k:
                keywords.extend(v)

        news_url  = "https://finnhub.io/api/v1/news?category=general&token=" + FINNHUB_KEY
        news_resp = req.get(news_url, timeout=10)
        all_news  = news_resp.json() if news_resp.status_code == 200 else []

        relevant_news = []
        for n in all_news[:100]:
            headline = (n.get("headline", "") + " " + n.get("summary", "")).lower()
            if any(kw in headline for kw in keywords):
                relevant_news.append({
                    "titre":  n.get("headline", ""),
                    "resume": n.get("summary", "")[:200]
                })
            if len(relevant_news) >= 8:
                break

        if len(relevant_news) < 3:
            for n in all_news[:8]:
                relevant_news.append({
                    "titre":  n.get("headline", ""),
                    "resume": n.get("summary", "")[:200]
                })

        news_text = ""
        for i, n in enumerate(relevant_news[:8]):
            news_text += str(i+1) + ". " + n["titre"] + "\n"
            if n["resume"]:
                news_text += "   " + n["resume"] + "\n"

        prompt = (
            "Tu es un analyste financier professionnel specialise en analyse fondamentale.\n\n"
            "ACTIF ANALYSE : " + asset.upper() + "\n\n"
            "ACTUALITES DU JOUR :\n" + news_text + "\n\n"
            "Analyse le sentiment du marche pour " + asset.upper() + " base sur ces actualites.\n\n"
            "Reponds UNIQUEMENT avec un JSON valide sans texte avant ni apres :\n"
            "{\n"
            "  \"sentiment\": \"HAUSSIER ou BAISSIER ou NEUTRE\",\n"
            "  \"confiance\": 72,\n"
            "  \"resume\": \"Resume en 2 phrases du contexte fondamental actuel\",\n"
            "  \"news_cles\": [\n"
            "    {\"titre\": \"titre court\", \"impact\": \"POSITIF ou NEGATIF ou NEUTRE\", \"explication\": \"explication courte\"},\n"
            "    {\"titre\": \"titre court\", \"impact\": \"POSITIF ou NEGATIF ou NEUTRE\", \"explication\": \"explication courte\"},\n"
            "    {\"titre\": \"titre court\", \"impact\": \"POSITIF ou NEGATIF ou NEUTRE\", \"explication\": \"explication courte\"}\n"
            "  ],\n"
            "  \"facteurs_surveillance\": [\"facteur 1\", \"facteur 2\", \"facteur 3\"],\n"
            "  \"conclusion\": \"Conclusion detaillee sur le contexte fondamental et ses implications. Ceci n est pas un conseil financier.\"\n"
            "}"
        )

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )

        result = clean_json(response.choices[0].message.content)
        result["actif"]   = asset.upper()
        result["nb_news"] = len(relevant_news)

        s = result.get("sentiment", "NEUTRE")
        if s == "HAUSSIER":
            result["sentiment_couleur"] = "#22c55e"
        elif s == "BAISSIER":
            result["sentiment_couleur"] = "#ef4444"
        else:
            result["sentiment_couleur"] = "#f97316"

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Historique — Sauvegarder une analyse ─────────────────────────────────────
@app.route("/save-analysis", methods=["POST"])
def save_analysis():
    try:
        data = request.json
        email = data.get("user_email")
        password = data.get("password")

        user = check_auth(email, password)
        if not user:
            return jsonify({"error": "Non autorise"}), 401

        # NETTOYAGE DE LA PROBABILITÉ
        raw_proba = str(data.get("probabilite", "0"))
        # On ne garde que les chiffres (enlève le % et le texte)
        clean_proba = "".join(filter(str.isdigit, raw_proba))
        proba_int = int(clean_proba) if clean_proba else 0

        # INSERTION
        res = supabase.table("analyses").insert({
            "user_email":   email,
            "asset":        data.get("asset"),
            "timeframe":    data.get("timeframe"),
            "modele":       data.get("modele"),
            "direction":    data.get("direction"),
            "entrees":      str(data.get("entrees")),
            "stop_loss":    str(data.get("stop_loss")),
            "take_profit":  str(data.get("take_profit")),
            "probabilite":  proba_int, # On envoie le chiffre propre
            "explication":  data.get("explication")
        }).execute()

        # Vérification si l'insertion a renvoyé des données
        if not res.data:
            return jsonify({"error": "Echec insertion Supabase (RLS ?)"}), 500

        return jsonify({"message": "Analyse enregistree", "id": res.data[0]["id"]})
    
    except Exception as e:
        print(f"ERREUR SERVEUR: {str(e)}") # Ceci s'affichera dans tes logs Render
        return jsonify({"error": str(e)}), 500


# ── Historique — Récupérer les analyses ──────────────────────────────────────
@app.route("/get-history", methods=["POST", "OPTIONS"])
def get_history():
    if request.method == "OPTIONS": return "", 204
    try:
        data     = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")
        user = check_auth(email, password)
        if not user:
            return jsonify({"error": "Non autorise. Connecte-toi."}), 401

        res = supabase.table("analyses") \
            .select("*") \
            .eq("user_email", email) \
            .order("created_at", desc=True) \
            .limit(50) \
            .execute()
        return jsonify({"analyses": res.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Historique — Mettre à jour le résultat d'un trade ────────────────────────
@app.route("/update-trade-result", methods=["POST", "OPTIONS"])
def update_trade_result():
    if request.method == "OPTIONS": return "", 204
    try:
        data      = request.get_json()
        email     = data.get("email", "").strip().lower()
        password  = data.get("password", "")
        analysis_id = data.get("id")
        result    = data.get("trade_result")  # "win" | "loss" | "skip" | null
        note      = data.get("trade_note", "")

        user = check_auth(email, password)
        if not user:
            return jsonify({"error": "Non autorise. Connecte-toi."}), 401

        # Vérifier que l'analyse appartient bien à cet utilisateur
        check = supabase.table("analyses").select("id").eq("id", analysis_id).eq("user_email", email).execute()
        if not check.data:
            return jsonify({"error": "Analyse introuvable"}), 404

        supabase.table("analyses").update({
            "trade_result": result,
            "trade_note":   note
        }).eq("id", analysis_id).execute()
        return jsonify({"message": "Resultat mis a jour"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Home ──────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return "API Trading IA active 🚀"


# ── Keep-alive ────────────────────────────────────────────────────────────────
def keep_alive():
    while True:
        time.sleep(840)
        try:
            urllib.request.urlopen("https://trading-ai-7y8g.onrender.com/")
        except:
            pass

thread = threading.Thread(target=keep_alive, daemon=True)
thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

























