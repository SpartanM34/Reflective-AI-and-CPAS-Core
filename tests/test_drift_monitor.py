import json
from pathlib import Path
from cpas_autogen import drift_monitor


def test_latest_averages(tmp_path, monkeypatch):
    log = [
        {
            "timestamp": "2025-01-01T00:00:00",
            "avg_7_day": {
                "interpretive_bandwidth": 0.5,
                "symbolic_density": 0.6,
                "divergence_space": 0.7,
            },
            "avg_30_day": {
                "interpretive_bandwidth": 0.4,
                "symbolic_density": 0.5,
                "divergence_space": 0.6,
            },
            "flexibility_pulse": 0.1,
        },
        {
            "timestamp": "2025-01-02T00:00:00",
            "avg_7_day": {
                "interpretive_bandwidth": 0.55,
                "symbolic_density": 0.65,
                "divergence_space": 0.75,
            },
            "avg_30_day": {
                "interpretive_bandwidth": 0.45,
                "symbolic_density": 0.55,
                "divergence_space": 0.65,
            },
            "flexibility_pulse": 0.2,
        },
    ]
    file = tmp_path / "drift.json"
    file.write_text(json.dumps(log))
    monkeypatch.setattr(drift_monitor, "DRIFT_LOG", file)

    avgs = drift_monitor.latest_averages()
    assert avgs["avg_7_day"]["interpretive_bandwidth"] == 0.55
    assert avgs["avg_30_day"]["divergence_space"] == 0.65
    assert avgs["flexibility_pulse"] == 0.2

    metrics = drift_monitor.latest_metrics()
    assert metrics["interpretive_bandwidth"] == 0.55
    assert metrics["symbolic_density"] == 0.65
    assert metrics["divergence_score"] == 0.75
