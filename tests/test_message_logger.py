import json
from pathlib import Path
from cpas_autogen import message_logger
from cpas_autogen.message_logger import log_message


def test_log_message_appends(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    monkeypatch.setattr(message_logger, "MANIFEST_FILE", path)
    monkeypatch.setattr(message_logger, "MAX_MANIFEST_SIZE", 10000)
    log_message("t1", "2025", "inst", "seed", "h1", "fp1")
    data = json.loads(path.read_text())
    assert data["messages"][0]["threadToken"] == "t1"


def test_rotation(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    monkeypatch.setattr(message_logger, "MANIFEST_FILE", path)
    monkeypatch.setattr(message_logger, "MAX_MANIFEST_SIZE", 200)
    log_message("t1", "2025", "inst", "seed", "h1", "fp1")
    log_message("t2", "2025", "inst", "seed", "h2", "fp2")
    rotated = list(tmp_path.glob("manifest-*.json"))
    assert rotated, "manifest should rotate when size exceeded"
    data = json.loads(path.read_text())
    assert len(data["messages"]) == 1
    assert data["messages"][0]["threadToken"] == "t2"
