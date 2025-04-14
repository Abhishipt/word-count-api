from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import threading
import time
import docx
import pdfplumber
import re

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def delete_file_later(path, delay=60):
    def remove():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=remove).start()

@app.route('/')
def home():
    return jsonify({'status': 'Word Counter API is running ✅'}), 200

def count_metrics(text):
    words = re.findall(r'\b\w+\b', text)
    characters = len(text)
    sentences = re.split(r'[.!?]+', text)
    paragraphs = text.strip().split("\n\n")
    return {
        "word_count": len(words),
        "character_count": characters,
        "sentence_count": len([s for s in sentences if s.strip()]),
        "paragraph_count": len([p for p in paragraphs if p.strip()])
    }

@app.route('/analyze', methods=['POST'])
def analyze_text():
    file = request.files.get('file')
    raw_text = ""

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    file_ext = filename.lower().split('.')[-1]
    file_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
    file.save(saved_path)

    try:
        if file_ext == "txt":
            with open(saved_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        elif file_ext == "pdf":
            with pdfplumber.open(saved_path) as pdf:
                raw_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        elif file_ext == "docx":
            doc = docx.Document(saved_path)
            raw_text = "\n".join([para.text for para in doc.paragraphs])
        else:
            delete_file_later(saved_path)
            return jsonify({"error": "Unsupported file format"}), 400

        delete_file_later(saved_path)
        return jsonify(count_metrics(raw_text))

    except Exception as e:
        print("❌ Error:", e)
        delete_file_later(saved_path)
        return jsonify({"error": "Failed to analyze file"}), 500

if __name__ == '__main__':
    app.run(debug=False)
