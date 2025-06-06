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

# Auto-delete after 1 minute
def delete_file_later(path, delay=60):
    def remove():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=remove).start()

@app.route('/')
def home():
    return jsonify({'status': 'Word Counter API is running ✅'}), 200

def count_metrics(text, include_sentences=False, include_paragraphs=False):
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    words = text.split()
    word_count = len([w for w in words if w.strip()])
    characters = len(text.rstrip('\n'))

    result = {
        "word_count": word_count,
        "character_count": characters
    }

    if include_sentences:
        sentences = re.split(r'[.!?]+', text)
        result["sentence_count"] = len([s for s in sentences if s.strip()])

    if include_paragraphs:
        paragraphs = text.strip().split('\n\n')
        result["paragraph_count"] = len([p for p in paragraphs if p.strip()])

    return result

@app.route('/analyze', methods=['POST'])
def analyze_text():
    file = request.files.get('file')
    raw_text = request.form.get('text', '').strip()

    include_sentences = request.form.get('include_sentences', 'false') == 'true'
    include_paragraphs = request.form.get('include_paragraphs', 'false') == 'true'

    if not file and not raw_text:
        return jsonify({"error": "No file or text provided"}), 400

    if file:
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

        except Exception as e:
            print("❌ Error:", e)
            delete_file_later(saved_path)
            return jsonify({"error": "Failed to analyze file"}), 500

    return jsonify(count_metrics(raw_text, include_sentences, include_paragraphs))

if __name__ == '__main__':
    app.run(debug=False)
