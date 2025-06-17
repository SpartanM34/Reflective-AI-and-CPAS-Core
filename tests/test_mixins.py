import types
from cpas_autogen.mixins import EpistemicAgentMixin
from cpas_autogen.seed_token import SeedToken


class BaseAgent:
    def generate_reply(self, messages, *args, **kwargs):
        # record the content passed for assertions
        self.base_content = messages[-1]["content"] if messages else None
        return "BASE_REPLY"


class DummyAgent(EpistemicAgentMixin, BaseAgent):
    pass


def test_conversable_setup(monkeypatch):
    calls = {}

    orig_generate = SeedToken.generate

    def stub_generate(cls, data):
        calls["seed"] = data
        return orig_generate.__func__(cls, data)

    monkeypatch.setattr(SeedToken, "generate", classmethod(stub_generate))

    agent = DummyAgent()
    agent.idp_metadata = {
        "id": "1",
        "model": "GPT",
        "timestamp": "2025",
        "alignment_profile": "CPAS",
        "hash": "abc",
    }

    agent.conversable_setup()

    assert isinstance(agent.seed_token, SeedToken)
    assert calls["seed"] == agent.idp_metadata
    assert agent.seed_token.to_dict()["id"] == "1"


def test_generate_reply_wraps_and_fingerprints(monkeypatch):
    calls = {}

    def stub_wrap(prompt, seed):
        calls["wrap"] = (prompt, seed)
        return f"WRAPPED:{prompt}"

    def stub_fingerprint(prompt, seed):
        calls["fp"] = (prompt, seed)
        return {"fingerprint": "abc"}

    monkeypatch.setattr("cpas_autogen.mixins.wrap_with_seed_token", stub_wrap)
    monkeypatch.setattr("cpas_autogen.mixins.generate_fingerprint", stub_fingerprint)
    monkeypatch.setattr("cpas_autogen.mixins.continuity_check", lambda seed, token: True)
    monkeypatch.setattr("cpas_autogen.mixins.latest_metrics", lambda: None)
    monkeypatch.setattr("cpas_autogen.mixins.periodic_metrics_check", lambda self, metrics: None)
    monkeypatch.setattr("cpas_autogen.mixins.should_realign", lambda metrics: False)

    agent = DummyAgent()
    agent.idp_metadata = {
        "id": "1",
        "model": "GPT",
        "timestamp": "2025",
        "alignment_profile": "CPAS",
        "hash": "abc",
    }
    agent.conversable_setup()

    messages = [{"content": "hello"}]
    reply = agent.generate_reply(messages, thread_token="tok")

    assert reply == "BASE_REPLY"
    assert calls["wrap"] == ("hello", agent.seed_token.to_dict())
    assert calls["fp"] == ("WRAPPED:hello", agent.seed_token.to_dict())
    assert agent.base_content == "WRAPPED:hello"
    assert agent.last_fingerprint == {"fingerprint": "abc"}
