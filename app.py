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
        image = request.files["image"]
        image_bytes = image.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """
Tu es un expert en trading technique (forex, crypto, actions).

Analyse ce screenshot de graphique TradingView.

1. Identifie si possible :
- la paire ou l’actif (ex: EUR/USD, BTCUSDT, AAPL)
- le timeframe (ex: M5, M15, H1, H4)

2. Détermine la direction principale :
BUY ou SELL

3. Propose :
- 2 zones possibles de point d’entrée
- 1 Stop Loss
- 2 Take Profit (TP1 et TP2)

4. Explique ton raisonnement (support, résistance, tendance, pattern, RSI, EMA, etc.)

Réponds STRICTEMENT au format JSON suivant :

{
  "marche": "nom du marché ou inconnu",
  "timeframe": "timeframe ou inconnu",
  "direction": "BUY ou SELL",
  "entrees": ["prix 1", "prix 2"],
  "stop_loss": "prix",
  "take_profit": ["tp1", "tp2"],
  "explication": "analyse claire et pédagogique en français"
}

Ne mets aucun texte en dehors du JSON.
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        result = response.choices[0].message.content
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)







