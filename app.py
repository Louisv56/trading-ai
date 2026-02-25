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
from openai import OpenAI
from supabase import create_client, Client
from datetime import date

# ── Clients ──────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

stripe.api_key  = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_PREMIUM   = os.getenv("STRIPE_PRICE_PREMIUM")
PRICE_PRO       = os.getenv("STRIPE_PRICE_PRO")
FRONTEND_URL    = os.getenv("FRONTEND_URL", "https://votre-site.com")

app = Flask(__name__)
CORS(app)

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

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

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
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

        user = get_user(email)
        if not user or user["password"] != hash_password(password):
            return jsonify({"error": "Non autorise. Connecte-toi."}), 401

        user  = reset_counter_if_needed(user)
        plan  = user["plan"]
        count = user["analyses_utilisees"]

        if plan == "free" and count >= 2:
            return jsonify({"error": "LIMIT_REACHED", "plan": "free"}), 403
        if plan == "premium" and count >= 50:
            return jsonify({"error": "LIMIT_REACHED", "plan": "premium"}), 403

        asset     = request.form.get("asset", "non precise")
        timeframe = request.form.get("timeframe", "non precise")

        prompt = (
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
            "Pour probabilite_succes : entier entre 0 et 100 base sur les confluences, "
            "la clarte de la structure et la qualite du R/R. "
            "Setup moyen = 50-60%, bon setup = 65-75%, excellent = 75-85%. "
            "Ne depasse jamais 85% car aucun trade n est certain."
        )

        messages_content = [{"type": "text", "text": prompt}]

        if "image_htf" in request.files and request.files["image_htf"].filename != "":
            img = request.files["image_htf"].read()
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img).decode()}
            })

        if "image_ltf" in request.files and request.files["image_ltf"].filename != "":
            img = request.files["image_ltf"].read()
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img).decode()}
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

        supabase.table("users").update({
            "analyses_utilisees": count + 1
        }).eq("id", user["id"]).execute()

        if plan == "free":
            result["analyses_restantes"] = max(0, 2 - (count + 1))
        elif plan == "premium":
            result["analyses_restantes"] = max(0, 50 - (count + 1))
        else:
            result["analyses_restantes"] = 999

        result["plan"] = plan

        # Pastille probabilite - calcul cote serveur
        score = result.get("probabilite_succes", 0)
        if isinstance(score, int) or isinstance(score, float):
            if score >= 70:
                result["proba_couleur"] = "#22c55e"
                result["proba_label"] = "Haute probabilite"
            elif score >= 50:
                result["proba_couleur"] = "#f97316"
                result["proba_label"] = "Probabilite neutre"
            else:
                result["proba_couleur"] = "#ef4444"
                result["proba_label"] = "Faible probabilite"

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stripe Checkout ───────────────────────────────────────────────────────────
@app.route("/create-checkout", methods=["POST"])
def create_checkout():
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
                supabase.table("users").update({
                    "stripe_customer_id": customer_id
                }).eq("id", user["id"]).execute()

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



# ── Cancel Subscription ───────────────────────────────────────────────────────
@app.route("/cancel-subscription", methods=["POST"])
def cancel_subscription():
    try:
        data     = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")

        user = get_user(email)
        if not user or user["password"] != hash_password(password):
            return jsonify({"error": "Non autorise"}), 401

        sub_id = user.get("stripe_subscription_id")
        if not sub_id:
            return jsonify({"error": "Aucun abonnement actif trouve"}), 400

        # Resiliation a la fin de la periode en cours (pas immediate)
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)

        return jsonify({"message": "Resiliation confirmee. Votre acces reste actif jusqu a la fin de la periode en cours."})

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



























