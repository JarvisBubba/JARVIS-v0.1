"""Serves the JARVIS site + people chat, stores chat messages."""
import os
import threading
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

MESSAGES = []
MAX_MESSAGES = 300
LOCK = threading.Lock()


@app.route("/")
def home():
    return send_from_directory(BASE, "index.html")


@app.route("/<path:filename>")
def site_files(filename):
    return send_from_directory(BASE, filename)


@app.get("/api/messages")
def get_messages():
    after = request.args.get("after", default=0, type=int)
    with LOCK:
        last = MESSAGES[-1]["id"] if MESSAGES else 0
        if after > last:
            after = 0
        msgs = [m for m in MESSAGES if m["id"] > after][-100:]
    return jsonify({"messages": msgs, "lastId": last})


@app.post("/api/messages")
def post_message():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "Guest").strip()[:24] or "Guest"
    text = (data.get("text") or "").strip()[:500]
    if not text:
        return jsonify({"ok": False, "error": "Message cannot be empty."}), 400
    with LOCK:
        mid = (MESSAGES[-1]["id"] + 1) if MESSAGES else 1
        msg = {"id": mid, "name": name, "text": text,
               "time": datetime.now().strftime("%H:%M:%S")}
        MESSAGES.append(msg)
        if len(MESSAGES) > MAX_MESSAGES:
            del MESSAGES[:-MAX_MESSAGES]
    return jsonify({"ok": True, "message": msg})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
