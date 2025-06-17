from __future__ import annotations

"""Simple Flask API for T-BEEP message storage.

This demo implementation stores messages in memory only. Future versions
may persist data to SQLite and require token-based authentication.
"""

from typing import Dict, List
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory message store keyed by thread token
MESSAGE_STORE: Dict[str, List[dict]] = {}


@app.route("/api/v1/messages", methods=["POST"])
def post_message():
    """Store a T-BEEP message in memory."""
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400
    thread_id = data.get("threadToken")
    if not thread_id:
        return jsonify({"error": "threadToken missing"}), 400
    MESSAGE_STORE.setdefault(thread_id, []).append(data)
    return jsonify({"status": "stored"}), 201


@app.route("/api/v1/messages", methods=["GET"])
def get_messages():
    """Return messages for the given thread ID."""
    thread_id = request.args.get("thread_id")
    if not thread_id:
        return jsonify({"error": "thread_id required"}), 400
    return jsonify(MESSAGE_STORE.get(thread_id, []))


if __name__ == "__main__":
    app.run(debug=True)
