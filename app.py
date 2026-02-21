
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "API Trading IA active 🚀"

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        messages_content = []

        # Récupération des infos contextuelles
        asset = request.form.get("asset", "non précisé")
        timeframe = request.form.get("timeframe", "non précisé")

        prompt = f"""
Tu es un trader professionnel spécialisé en analyse technique Smart Money Concepts (SMC).

CONTEXTE FOURNI PAR L'UTILISATEUR :
- Actif : {asset}
- Timeframe principal : {timeframe}

MÉTHODOLOGIE À APPLIQUER :
- Identifier la structure de marché : Higher High/Higher Low (haussier) ou Lower High/Lower Low (baissier)
- Repérer les zones institutionnelles : Order Blocks, Fair Value Gaps (FVG), Breaker Blocks
- Identifier les liquidity pools : Equal Highs/Lows, BSL/SSL (Buy Side / Sell Side Liquidity)
- Analyser le flux des ordres : BOS (Break of Structure), CHOCH (Change of Character)
- Sur le LTF (si fourni) : chercher le point d'entrée optimal dans la zone HTF identifiée

Tu peux recevoir un ou deux graphiques :
- Un seul graphique : fais une analyse classique complète
- Deux graphiques (HTF + LTF) : fais une analyse multi-timeframe avec confluence

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après, sans backticks, dans ce format exact :

{{
  "direction": "BUY ou SELL ou NEUTRE",
  "entrees": ["niveau précis 1", "niveau précis 2"],
  "stop_loss": "niveau précis avec justification courte",
  "take_profit": ["TP1 - niveau", "TP2 - niveau", "TP3 - niveau"],
  "ratio_risque_rendement": "ex: 1:3",
  "confluences": ["confluence 1", "confluence 2", "confluence 3"],
  "invalidation": "condition qui invalide le setup",
  "explication": "Analyse détaillée en français : tendance, structure, zones clés, pattern, raisonnement SMC. Ceci est une analyse automatisée et ne constitue pas un conseil financier."
}}
"""

        messages_content.append({"type": "text", "text": prompt})

        # Image HTF si fournie
        if "image_htf" in request.files and request.files["image_htf"].filename != "":
            image_htf = request.files["image_htf"]
            image_htf_base64 = base64.b64encode(image_htf.read()).decode("utf-8")
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_htf_base64}"}
            })

        # Image LTF si fournie
        if "image_ltf" in request.files and request.files["image_ltf"].filename != "":
            image_ltf = request.files["image_ltf"]
            image_ltf_base64 = base64.b64encode(image_ltf.read()).decode("utf-8")
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_ltf_base64}"}
            })

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": messages_content
                }
            ],
            max_tokens=1200
        )

        raw = response.choices[0].message.content.strip()

        # Nettoyage des backticks markdown au cas où
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

















