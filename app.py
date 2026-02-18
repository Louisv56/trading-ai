
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import os
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

        prompt = """
Tu es un expert en trading (forex, crypto, actions).

Tu peux recevoir soit :
- un seul graphique
- ou deux graphiques (HTF = timeframe haut, LTF = timeframe bas) : l'objectif du LowTimeFrame est de rentrer sur le marché avec le meilleur point d'entrée, Tandis ce que l'image avec la timeframe haute sert uniquement de visualisation global du marché, de confluense avec la LowTimeFrames ect

Si un seul graphique est fourni, fais une analyse classique.
Si deux graphiques sont fournis, fais une analyse multi-timeframe (confluence HTF + LTF).

Donne une analyse en français avec ce format EXACT :

Marché :
Timeframe(s) :
Direction (BUY ou SELL) :

Zone(s) d’entrée :
- entrée 1
- entrée 2

Stop Loss :
Take Profit :
- TP1
- TP2
- TP3

Analyse :
Explique clairement ton raisonnement (tendance, support/résistance, structure, pattern).

Termine par :
"Ceci est une analyse automatisée et ne constitue pas un conseil financier."
"""

        messages_content.append({"type": "text", "text": prompt})

        # image HTF si fournie
        if "image_htf" in request.files and request.files["image_htf"].filename != "":
            image_htf = request.files["image_htf"]
            image_htf_base64 = base64.b64encode(image_htf.read()).decode("utf-8")
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_htf_base64}"}
            })

        # image LTF si fournie
        if "image_ltf" in request.files and request.files["image_ltf"].filename != "":
            image_ltf = request.files["image_ltf"]
            image_ltf_base64 = base64.b64encode(image_ltf.read()).decode("utf-8")
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_ltf_base64}"}
            })

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": messages_content
                }
            ],
            max_tokens=500
        )

        result = response.choices[0].message.content
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)














