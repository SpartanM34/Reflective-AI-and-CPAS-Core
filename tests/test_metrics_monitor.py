import pytest
import json
from pathlib import Path
from cpas_autogen import metrics_monitor


def test_load_baseline(tmp_path, monkeypatch):
    data = {"2025": {"x": 1.0}}
    f = tmp_path / "baseline.json"
    f.write_text(json.dumps(data))
    monkeypatch.setattr(metrics_monitor, "BASELINE_FILE", f)
    assert metrics_monitor.load_baseline() == {"x": 1.0}


def test_diff_report(monkeypatch):
    monkeypatch.setattr(metrics_monitor, "load_baseline", lambda: {"a": 1.0})
    report = metrics_monitor.diff_report({"a": 1.2})
    assert report["a"]["delta"] == pytest.approx(0.2)
    assert "similarity" in report
