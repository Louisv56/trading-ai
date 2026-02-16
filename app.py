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
Tu es un expert en trading (forex, crypto, actions).

Analyse ce screenshot de graphique TradingView.

Donne une analyse complète en français avec ce format EXACT :

Marché :
Timeframe :
Direction (BUY ou SELL) :

Zone(s) d’entrée :
- entrée 1
- entrée 2

Stop Loss :
Take Profit :
- TP1
- TP2

Analyse :
Explique clairement pourquoi (tendance, support/résistance, pattern, indicateurs visibles).

Termine par :
"Ceci est une analyse automatisée et ne constitue pas un conseil financier."
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








