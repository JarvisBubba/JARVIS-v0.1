"""Local J.A.R.V.I.S. chat server."""
import re

from flask import Flask, jsonify, render_template, request

from jarvis_core import HELP, handle

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    # Allow people to type "@jarvis help" if they want.
    message = re.sub(r"^@jarvis\b\s*", "", message, flags=re.I).strip()

    answer = handle(message) if message else HELP

    if answer is None:
        answer = (
            "I don't have a protocol for that yet, sir. "
            "Try `help` to see what I can do."
        )

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
