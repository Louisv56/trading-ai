from flask import Flask, request, jsonify
import openai
import base64

openai.api_key = "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"

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

app.run(host="0.0.0.0", port=5000)
