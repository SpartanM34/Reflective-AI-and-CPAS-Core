import json
from tools import wonder_index_calculator as wic


def test_load_wonder_signals_text(tmp_path):
    file = tmp_path / "signals.json"
    file.write_text(json.dumps([{"timestamp": "2025-01-01T00:00:00", "text": "hi"}]))
    result = wic.load_wonder_signals(file)
    assert "2025-01-01T00:00:00" in result
    assert result["2025-01-01T00:00:00"]["wonder_signal"] == min(len("hi")/100.0, 1.0)

