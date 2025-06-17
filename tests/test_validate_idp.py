import pytest
pytest.importorskip("jsonschema")
import runpy

validate_module = runpy.run_path("instances/schema/validation-tools/validate_idp.py")
validate_instance = validate_module["validate_instance"]


def test_validate_instance_pass(capsys):
    instance = "agents/json/openai-gpt4/Clarence-9.json"
    schema = "instances/schema/current/idp-v1.0-schema.json"
    validate_instance(instance, schema)
    captured = capsys.readouterr().out
    assert "Validation passed" in captured
