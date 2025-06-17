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
