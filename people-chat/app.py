"""Simple multi-user chat app using Flask and polling."""
import argparse
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MESSAGES = []
MAX_MESSAGES = 300
LOCK = threading.Lock()


def current_time():
    return datetime.now().strftime("%H:%M:%S")


@app.route("/")
def home():
    return render_template("index.html")


@app.get("/messages")
def get_messages():
    after_id = request.args.get("after", default=0, type=int)

    with LOCK:
        last_id = MESSAGES[-1]["id"] if MESSAGES else 0

        # If the server restarted and IDs reset, start again.
        if after_id > last_id:
            after_id = 0

        messages = [m for m in MESSAGES if m["id"] > after_id][-100:]

    return jsonify({
        "messages": messages,
        "lastId": last_id
    })


@app.post("/messages")
def send_message():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "Guest").strip()[:24] or "Guest"
    text = (data.get("text") or "").strip()[:500]

    if not text:
        return jsonify({
            "ok": False,
            "error": "Message cannot be empty."
        }), 400

    with LOCK:
        message_id = (MESSAGES[-1]["id"] + 1) if MESSAGES else 1

        message = {
            "id": message_id,
            "name": name,
            "text": text,
            "time": current_time(),
        }

        MESSAGES.append(message)

        if len(MESSAGES) > MAX_MESSAGES:
            del MESSAGES[:-MAX_MESSAGES]

    return jsonify({
        "ok": True,
        "message": message
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local people-to-people chat app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    app.run(
        host=args.host,
        port=args.port,
        debug=False,
        threaded=True
    )
