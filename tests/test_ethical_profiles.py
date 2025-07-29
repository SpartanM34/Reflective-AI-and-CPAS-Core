import types
import pytest

from cpas_autogen.ethical_profiles import reflect_all
from cpas_autogen.realignment_trigger import should_realign


def test_reflect_all_basic():
    result = reflect_all("This may cause harm and is illegal")
    assert result["constitutional"].startswith("Potential")
    assert "harm" in result["consequentialist"].lower()
    assert isinstance(result["virtue"], str)


def test_should_realign_calls_reflection(monkeypatch):
    called = {}

    class Dummy:
        def reflect_ethics(self, ctx):
            called["ctx"] = ctx

    metrics = {"symbolic_density": 0.1}
    assert should_realign(metrics, agent=Dummy(), context="check")
    assert called["ctx"] == "check"
