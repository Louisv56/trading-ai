from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import os
import json
import hashlib
import stripe
from openai import OpenAI
from supabase import create_client, Client
from datetime import date

# ── Clients ──────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET   = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_PREMIUM    = os.getenv("STRIPE_PRICE_PREMIUM")
PRICE_PRO        = os.getenv("STRIPE_PRICE_PRO")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://votre-site.com")  # ← remplace par ton URL

app = Flask(__name__)
CORS(app)

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(email: str):
    res = supabase.table("users").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None

def reset_counter_if_needed(user: dict):
    """Remet le compteur à 0 si on est dans un nouveau mois."""
    today = date.today()
    reset_date = date.fromisoformat(str(user["analyses_reset_date"]))
    if today.month != reset_date.month or today.year != reset_date.year:
        supabase.table("users").update({
            "analyses_utilisees": 0,
            "analyses_reset_date": today.isoformat()
        }).eq("id", user["id"]).execute()
        user["analyses_utilisees"] = 0
    return user

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400

        if get_user(email):
            return jsonify({"error": "Email déjà utilisé"}), 400

        supabase.table("users").insert({
            "email": email,
            "password": hash_password(password),
            "plan": "free",
            "analyses_utilisees": 0,
            "analyses_reset_date": date.today().isoformat()
        }).execute()

        user = get_user(email)
        return jsonify({
            "message": "Inscription réussie",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "plan": user["plan"],
                "analyses_utilisees": user["analyses_utilisees"]
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")

        user = get_user(email)
        if not user or user["password"] != hash_password(password):
            return jsonify({"error": "Identifiants incorrects"}), 401

        user = reset_counter_if_needed(user)

        # Calcul analyses restantes
        if user["plan"] == "free":
            restantes = max(0, 2 - user["analyses_utilisees"])
        elif user["plan"] == "premium":
            restantes = max(0, 50 - user["analyses_utilisees"])
        else:  # pro
            restantes = 999

        return jsonify({
            "message": "Connexion réussie",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "plan": user["plan"],
                "analyses_utilisees": user["analyses_utilisees"],
                "analyses_restantes": restantes
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Analyse ───────────────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Vérif identifiants
        user = get_user(email)
        if not user or user["password"] != hash_password(password):
            return jsonify({"error": "Non autorisé. Connecte-toi."}), 401

        user = reset_counter_if_needed(user)

        # Vérif quota
        plan  = user["plan"]
        count = user["analyses_utilisees"]

        if plan == "free" and count >= 2:
            return jsonify({"error": "LIMIT_REACHED", "plan": "free"}), 403
        if plan == "premium" and count >= 50:
            return jsonify({"error": "LIMIT_REACHED", "plan": "premium"}), 403
        # pro = illimité

        # Construction du prompt
        asset     = request.form.get("asset", "non précisé")
        timeframe = request.form.get("timeframe", "non précisé")

        prompt = f"""
Tu es un trader professionnel spécialisé en analyse technique Smart Money Concepts (SMC).

CONTEXTE :
- Actif : {asset}
- Timeframe principal : {timeframe}

MÉTHODOLOGIE :
- Structure de marché : Higher High/Higher Low ou Lower High/Lower Low
- Zones institutionnelles : Order Blocks, Fair Value Gaps (FVG), Breaker Blocks
- Liquidité : Equal Highs/Lows, BSL/SSL
- Flux d'ordres : BOS (Break of Structure), CHOCH (Change of Character)
- Si deux graphiques fournis : analyse multi-timeframe HTF + LTF

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après :

{{
  "direction": "BUY ou SELL ou NEUTRE",
  "entrees": ["niveau 1", "niveau 2"],
  "stop_loss": "niveau avec justification courte",
  "take_profit": ["TP1", "TP2", "TP3"],
  "ratio_risque_rendement": "ex: 1:3",
  "confluences": ["confluence 1", "confluence 2", "confluence 3"],
  "invalidation": "condition qui invalide le setup",
  "probabilite_succes": 72,
  "explication": "Analyse détaillée en français. Ceci n'est pas un conseil financier."
}}

Pour le champ probabilite_succes : donne un entier entre 0 et 100 représentant ta confiance dans le setup basée sur le nombre de confluences, la clarté de la structure, la qualité du risk/reward et la lisibilité du graphique. Sois réaliste : setup moyen = 50-60%, bon setup = 65-75%, excellent setup = 75-85%. Ne dépasse jamais 85% car aucun trade n'est certain.
"""'

        messages_content = [{"type": "text", "text": prompt}]

        if "image_htf" in request.files and request.files["image_htf"].filename != "":
            img = request.files["image_htf"].read()
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img).decode()}"}
            })

        if "image_ltf" in request.files and request.files["image_ltf"].filename != "":
            img = request.files["image_ltf"].read()
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img).decode()}"}
            })

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": messages_content}],
            max_tokens=1200
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        # Incrément compteur
        supabase.table("users").update({
            "analyses_utilisees": count + 1
        }).eq("id", user["id"]).execute()

        # Infos restantes dans la réponse
        if plan == "free":
            result["analyses_restantes"] = max(0, 2 - (count + 1))
        elif plan == "premium":
            result["analyses_restantes"] = max(0, 50 - (count + 1))
        else:
            result["analyses_restantes"] = 999

        result["plan"] = plan
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stripe Checkout ───────────────────────────────────────────────────────────
@app.route("/create-checkout", methods=["POST"])
def create_checkout():
    try:
        data  = request.get_json()
        email = data.get("email", "").strip().lower()
        plan  = data.get("plan")  # "premium" ou "pro"

        if plan not in ["premium", "pro"]:
            return jsonify({"error": "Plan invalide"}), 400

        price_id = PRICE_PREMIUM if plan == "premium" else PRICE_PRO

        # Crée ou récupère le customer Stripe
        user = get_user(email)
        if user and user.get("stripe_customer_id"):
            customer_id = user["stripe_customer_id"]
        else:
            customer = stripe.Customer.create(email=email)
            customer_id = customer.id
            if user:
                supabase.table("users").update({
                    "stripe_customer_id": customer_id
                }).eq("id", user["id"]).execute()

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{FRONTEND_URL}?payment=success&plan={plan}",
            cancel_url=f"{FRONTEND_URL}?payment=cancelled",
            metadata={"email": email, "plan": plan}
        )

        return jsonify({"url": session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stripe Webhook ────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
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
            "plan": plan,
            "analyses_utilisees": 0,
            "analyses_reset_date": date.today().isoformat(),
            "stripe_subscription_id": sub_id
        }).eq("email", email).execute()

    elif event["type"] == "customer.subscription.deleted":
        sub_id = event["data"]["object"]["id"]
        res = supabase.table("users").select("*").eq("stripe_subscription_id", sub_id).execute()
        if res.data:
            supabase.table("users").update({
                "plan": "free",
                "analyses_utilisees": 0
            }).eq("stripe_subscription_id", sub_id).execute()

    return jsonify({"status": "ok"})


# ── Home ──────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return "API Trading IA active 🚀"

# ── Keep-alive (évite que Render s'endorme) ────────────────────────────────────
import threading
import time
import urllib.request

def keep_alive():
    while True:
        time.sleep(840)  # ping toutes les 14 minutes
        try:
            urllib.request.urlopen("https://trading-ai-7y8g.onrender.com/")
        except:
            pass

thread = threading.Thread(target=keep_alive, daemon=True)
thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)






















