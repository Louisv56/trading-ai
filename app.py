
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

        prompt = """
Tu es un expert en trading (forex, crypto, actions).
Tu peux recevoir un ou deux graphiques (HTF et/ou LTF).: l'objectif du LowTimeFrame est de rentrer sur le marché avec le meilleur point d'entrée, Tandis ce que l'image avec la timeframe haute sert uniquement de visualisation global du marché, de confluense avec la LowTimeFrames ect
Analyse le ou les graphiques et réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après, dans ce format exact :

{
  "direction": "BUY ou SELL",
  "entrees": ["niveau1", "niveau2"],
  "stop_loss": "niveau",
  "take_profit": ["TP1", "TP2", "TP3"],
  "explication": "Ton analyse complète ici en français. Tendance, structure, support/résistance, pattern. Ceci est une analyse automatisée et ne constitue pas un conseil financier."
}
"""
        messages_content.append({"type": "text", "text": prompt})

        if "image_htf" in request.files and request.files["image_htf"].filename != "":
            image_htf = request.files["image_htf"]
            image_htf_base64 = base64.b64encode(image_htf.read()).decode("utf-8")
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_htf_base64}"}
            })

        if "image_ltf" in request.files and request.files["image_ltf"].filename != "":
            image_ltf = request.files["image_ltf"]
            image_ltf_base64 = base64.b64encode(image_ltf.read()).decode("utf-8")
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_ltf_base64}"}
            })

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # ✅ nom correct
            messages=[
                {
                    "role": "user",
                    "content": messages_content
                }
            ],
            max_tokens=1000  # ✅ suffisant pour une vraie analyse
        )

        raw = response.choices[0].message.content

        # Nettoyage au cas où il y aurait des backticks markdown
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)  # ✅ on parse le JSON proprement
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)















