import logging
import types

from instances.python import Lumin


class DummyAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.idp_metadata = None
        self.seed_token = None

    def generate_reply(self, *args, **kwargs):
        return "mock"


def test_create_agent_has_seed_token(monkeypatch):
    monkeypatch.setattr(Lumin, "ConversableAgent", DummyAgent)
    Lumin.config_list = [{}]
    agent = Lumin.create_agent()
    assert hasattr(agent, "seed_token")
    assert agent.seed_token is not None


def test_send_message_warns_on_continuity_failure(monkeypatch, caplog):
    monkeypatch.setattr(Lumin, "ConversableAgent", DummyAgent)
    Lumin.config_list = [{}]
    agent = Lumin.create_agent()
    caplog.set_level(logging.WARNING)
    Lumin.send_message(agent, "hello", thread_token="INVALID")
    assert any("Continuity check failed" in r.getMessage() for r in caplog.records)
