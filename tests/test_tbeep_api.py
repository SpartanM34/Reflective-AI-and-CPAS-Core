import pytest
pytest.importorskip("flask")
import json
from api.tbeep_api import app, MESSAGE_STORE


def test_post_and_get_message():
    client = app.test_client()
    MESSAGE_STORE.clear()
    msg = {
        "threadToken": "#TEST_001.0",
        "instance": "Unit",
        "reasoningLevel": "Detailed",
        "confidence": "High",
        "collaborationMode": "Discussion",
        "timestamp": "2025-01-01T00:00:00Z",
        "version": "#TEST.v1.0",
        "content": "hello"
    }
    res = client.post("/api/v1/messages", json=msg)
    assert res.status_code == 201
    res = client.get("/api/v1/messages", query_string={"thread_id": "#TEST_001.0"})
    assert res.status_code == 200
    assert res.get_json() == [msg]


def test_missing_thread_token():
    client = app.test_client()
    MESSAGE_STORE.clear()
    res = client.post("/api/v1/messages", json={"content": "x"})
    assert res.status_code == 400
