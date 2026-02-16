from flask import Flask, request, jsonify
import openai
import base64

import os
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    image = request.files["image"]
    image_bytes = image.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
    Tu es un expert en trading technique.
    Analyse ce graphique.
    Réponds uniquement en JSON avec :
    {
      "direction": "BUY ou SELL",
      "entry": "prix",
      "stop_loss": "prix",
      "take_profit": "prix",
      "commentaire": "brève explication"
    }
    """

    response = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
            ]}
        ]
    )

    result = response["choices"][0]["message"]["content"]
    return jsonify(result)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



