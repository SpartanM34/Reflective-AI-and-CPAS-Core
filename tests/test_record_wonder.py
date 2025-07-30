import json
import sys
from pathlib import Path
from tools import record_wonder


def test_record_wonder_appends_json(tmp_path, monkeypatch):
    file = tmp_path / "signals.json"
    monkeypatch.setattr(sys, "argv", ["record_wonder.py", "hello", "--file", str(file)])
    record_wonder.main()
    data = json.loads(file.read_text())
    assert data[0]["text"] == "hello"

    monkeypatch.setattr(sys, "argv", ["record_wonder.py", "world", "--file", str(file)])
    record_wonder.main()
    data = json.loads(file.read_text())
    assert len(data) == 2

