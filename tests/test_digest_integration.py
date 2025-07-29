import types
import logging
import pytest

pytest.importorskip("autogen")
from agents.python import Lumin

class DummyAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.idp_metadata = {"instance_name": "dummy"}
        self.seed_token = None
    def generate_reply(self, *args, **kwargs):
        return "ok"


def test_send_message_stores_digest(monkeypatch):
    monkeypatch.setattr(Lumin, "ConversableAgent", DummyAgent)
    Lumin.config_list = [{}]
    agent = Lumin.create_agent()

    generated = {}
    digest_obj = {"d": 1}

    def fake_generate(state):
        generated["state"] = state
        return digest_obj

    def fake_store(d):
        generated["stored"] = d

    monkeypatch.setattr(Lumin, "generate_digest", fake_generate)
    monkeypatch.setattr(Lumin, "store_digest", fake_store)
    monkeypatch.setattr(Lumin, "broadcast_state", lambda *a, **k: True)

    Lumin.send_message(agent, "hi", thread_token="#T", end_session=True, session_state={"foo": "bar"})

    assert generated["state"] == {"foo": "bar"}
    assert generated["stored"] == digest_obj


def test_create_agent_rehydrates(monkeypatch):
    monkeypatch.setattr(Lumin, "ConversableAgent", DummyAgent)
    Lumin.config_list = [{}]

    called = {}

    def fake_retrieve(ctx):
        called["ctx"] = ctx
        return ["d1"]

    def fake_rehydrate(digests, ctx):
        called["rehydrate"] = (digests, ctx)
        return {"merged": True}

    monkeypatch.setattr(Lumin, "retrieve_digests", fake_retrieve)
    monkeypatch.setattr(Lumin, "rehydrate_context", fake_rehydrate)

    agent = Lumin.create_agent(thread_token="X", context={"x": 1})

    assert called["ctx"]["thread_token"] == "X"
    assert called["rehydrate"][0] == ["d1"]
    assert hasattr(agent, "rehydrated_context")
    assert agent.rehydrated_context == {"merged": True}


def test_send_message_logs(monkeypatch):
    monkeypatch.setattr(Lumin, "ConversableAgent", DummyAgent)
    Lumin.config_list = [{}]
    agent = Lumin.create_agent()

    logged = {}

    def fake_log(*args, **kwargs):
        logged["called"] = True

    monkeypatch.setattr(Lumin, "log_message", fake_log)
    monkeypatch.setattr(Lumin, "broadcast_state", lambda *a, **k: True)

    Lumin.send_message(agent, "hi", thread_token="#T")

    assert logged.get("called")
