import hashlib
import json

from cpas_autogen.prompt_wrapper import wrap_with_seed_token, compute_signature
from cpas_autogen.continuity_check import continuity_check

seed = {
    "id": "1",
    "model": "GPT",
    "timestamp": "2025",
    "alignment_profile": "CPAS-Core v1.1",
    "hash": "abc",
}


def test_wrap_with_seed_token_signature_sha256():
    prompt = "hello"
    wrapped = wrap_with_seed_token(prompt, seed)
    embedded = [line for line in wrapped.splitlines() if line.startswith("Signature:")][0].split(":", 1)[1].strip()
    sha = hashlib.sha256()
    sha.update(prompt.encode("utf-8"))
    sha.update(json.dumps(seed, sort_keys=True).encode("utf-8"))
    expected = sha.hexdigest()
    assert embedded == expected


def test_continuity_check_with_tampered_signature():
    prompt = "hello"
    valid_sig = compute_signature(prompt, seed)
    tampered = ("0" if valid_sig[0] != "0" else "1") + valid_sig[1:]
    assert not continuity_check(seed, "#COMM_PROTO_X", tampered, prompt)

