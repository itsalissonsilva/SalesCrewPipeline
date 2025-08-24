# sales_ai/server.py
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

# Load .env once
load_dotenv()

from .crewapp import answer_question
from .core import _load_df

# Resolve /static at project root:  <project>/static
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")


@app.get("/")
def index():
    # Serve the static index.html from /static
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.get("/dataset")
def dataset():
    """Return a preview of the dataset as JSON (no HTML ever)."""
    try:
        limit = int(request.args.get("limit", "50"))
        limit = max(1, min(limit, 500))
        df = _load_df()
        preview = df.head(limit)
        return jsonify({
            "columns": list(preview.columns),
            "rows": preview.astype(str).values.tolist(),
            "total_rows": int(len(df)),
            "limit": limit,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Missing 'question'"}), 400
    try:
        res = answer_question(question)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "5000"))
    # bind to all interfaces so Docker can expose the port
    app.run(host="0.0.0.0", port=port, debug=False)




