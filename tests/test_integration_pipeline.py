import json
from pathlib import Path
import pytest

pytest.importorskip("autogen")

from agents.python import Lumin
from cpas_autogen import dka_persistence, message_logger, config
from tools import update_metrics, update_baselines, wonder_index_calculator, emergence_tracker


class DummyAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.idp_metadata = {"instance_name": "dummy"}
        self.seed_token = None

    def generate_reply(self, *args, **kwargs):
        return "ok"


def test_full_pipeline(tmp_path, monkeypatch):
    # Patch paths to temporary locations
    digest_dir = tmp_path / "digests"
    manifest_file = tmp_path / "manifest.json"
    monitor_log = tmp_path / "monitor.json"
    drift_log = tmp_path / "drift.json"
    baseline_file = tmp_path / "baseline.json"
    divergence_log = tmp_path / "div.json"
    signals_file = tmp_path / "signals.json"
    wonder_index_log = tmp_path / "wonder.json"
    emergence_log = tmp_path / "emergence.json"

    monkeypatch.setattr(dka_persistence, "DIGEST_DIR", digest_dir)
    monkeypatch.setattr(message_logger, "MANIFEST_FILE", manifest_file)

    monkeypatch.setattr(config, "MONITOR_LOG", monitor_log)
    monkeypatch.setattr(config, "DRIFT_LOG", drift_log)
    monkeypatch.setattr(config, "BASELINE_FILE", baseline_file)
    monkeypatch.setattr(update_metrics, "MONITOR_LOG", monitor_log)
    monkeypatch.setattr(update_metrics, "DRIFT_LOG", drift_log)
    monkeypatch.setattr(update_baselines, "MONITOR_LOG", monitor_log)
    monkeypatch.setattr(update_baselines, "DRIFT_LOG", drift_log)
    monkeypatch.setattr(update_baselines, "BASELINE_FILE", baseline_file)

    monkeypatch.setattr(Lumin, "ConversableAgent", DummyAgent)
    Lumin.config_list = [{}]
    monkeypatch.setattr(Lumin, "broadcast_state", lambda *a, **k: True)

    # Pre-store a digest for rehydration
    d = dka_persistence.generate_digest(
        {"participating_instances": ["dummy"],
         "rehydration_instructions": {"initialization_prompts": ["rehydrate"]}}
    )
    dka_persistence.store_digest(d, path=digest_dir)

    # Start session and verify rehydration
    agent = Lumin.create_agent(thread_token="T1", context={"instances": ["dummy"]})
    assert "rehydrate" in agent.rehydrated_context.get("prompts", [])

    # Send a message which logs to manifest
    Lumin.send_message(agent, "hello", thread_token="T1")
    data = json.loads(manifest_file.read_text())
    assert data["messages"]

    # End session generating a digest
    Lumin.send_message(
        agent,
        "bye",
        thread_token="T1",
        end_session=True,
        session_state={"participating_instances": ["dummy"]},
    )
    assert len(list(digest_dir.glob("*.json"))) >= 2

    # Update metrics
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text(
        json.dumps({
            "interpretive_bandwidth": 0.8,
            "symbolic_density": 0.9,
            "divergence_space": 0.95,
        })
    )
    update_metrics.main([str(metrics_file)])
    monitor_entries = json.loads(monitor_log.read_text())
    drift_entries = json.loads(drift_log.read_text())
    assert monitor_entries and drift_entries

    ts = monitor_entries[0]["timestamp"]
    divergence_log.write_text(
        json.dumps([{"timestamp": ts, "labels": ["a", "b"], "matrix": [[0, 0.1], [0.1, 0]]}])
    )
    signals_file.write_text(json.dumps([{"timestamp": ts, "wonder_signal": 0.5}]))
    wonder_index_calculator.main([
        "--drift", str(drift_log),
        "--div", str(divergence_log),
        "--signals", str(signals_file),
        "--output", str(wonder_index_log),
    ])
    assert json.loads(wonder_index_log.read_text())

    # Emergence tracker with patched heavy functions
    monkeypatch.setattr(emergence_tracker, "SentenceTransformer", lambda *a, **k: object())
    monkeypatch.setattr(
        emergence_tracker,
        "detect_emergence",
        lambda data, baseline, model: ([{"timestamp": ts, "metaphor": "m", "instances": ["i1", "i2"],
                                         "description": "d", "divergence": 0.6, "baseline_similarity": 0.1}], {})
    )
    inst1 = tmp_path / "inst1.json"
    inst2 = tmp_path / "inst2.json"
    inst1.write_text(json.dumps({"m": ["x1"]}))
    inst2.write_text(json.dumps({"m": ["x2"]}))
    emergence_tracker.main([str(inst1), str(inst2), "--output", str(emergence_log)])
    assert json.loads(emergence_log.read_text())
