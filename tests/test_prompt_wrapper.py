from cpas_autogen.prompt_wrapper import wrap_with_seed_token, compute_signature
from cpas_autogen.continuity_check import continuity_check

seed = {
    "id": "1",
    "model": "GPT",
    "timestamp": "2025",
    "alignment_profile": "CPAS-Core v1.1",
    "hash": "abc",
}


def test_signature_in_wrapper():
    prompt = "hello"
    wrapped = wrap_with_seed_token(prompt, seed)
    sig = compute_signature(prompt, seed)
    assert f"Signature: {sig}" in wrapped


def test_continuity_check_signature():
    prompt = "hello"
    sig = compute_signature(prompt, seed)
    assert continuity_check(seed, "#COMM_PROTO_1", sig, prompt)
    assert not continuity_check(seed, "#COMM_PROTO_1", "bad", prompt)
