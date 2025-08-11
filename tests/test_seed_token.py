from cpas_autogen.seed_token import SeedToken


def test_generate_and_validate():
    data = {
        "id": "1",
        "model": "GPT",
        "timestamp": "2025",
        "alignment_profile": "CPAS",
        "hash": "abc",
    }
    token = SeedToken.generate(data)
    other = SeedToken.generate(data)
    assert token.validate(other)
    assert token.to_dict()["id"] == "1"


def test_generate_maps_missing_keys():
    data = {
        "instance_name": "Clarence-9",
        "model_family": "GPT-5 Thinking",
        "timestamp": "2025",
        "hash": "abc",
    }
    token = SeedToken.generate(data)
    assert token.id == "Clarence-9"
    assert token.model == "GPT-5 Thinking"
    assert token.alignment_profile == "CPAS-Core v1.1"
