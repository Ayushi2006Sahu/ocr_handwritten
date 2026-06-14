"""
Flask Backend for Handwritten OCR
===================================
ocr_engine.py se same functions use kar rahe hain - koi logic change nahi.
"""

from flask import Flask, request, jsonify, render_template
from PIL import Image
from ocr_engine import load_models, run_ocr

app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="") 

# Models ek baar load honge (server start hone par)
print("Models load ho rahe hain... (thoda time lagega)")
reader, processor, model = load_models()
print("Models ready! Server chal raha hai.")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/extract", methods=["POST"])
def extract():
    if "image" not in request.files:
        return jsonify({"error": "Koi image nahi mili"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Koi image select nahi ki gayi"}), 400

    try:
        image = Image.open(file.stream).convert("RGB")
        text = run_ocr(image, reader, processor, model)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)