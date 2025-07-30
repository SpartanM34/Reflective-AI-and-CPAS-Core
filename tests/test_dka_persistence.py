import json
import hashlib
from cpas_autogen import dka_persistence


def test_generate_digest_keys():
    state = {
        "participating_instances": ["A", "B"],
        "metaphor_category": "Navigation",
        "library_version": "MLib-v0.1",
    }
    digest = dka_persistence.generate_digest(state)
    assert digest["digest_version"] == "1.0"
    assert digest["participating_instances"] == ["A", "B"]
    assert digest["digest_id"].startswith("DKA_")
    assert digest["metaphor_category"] == "Navigation"
    assert digest["library_version"] == "MLib-v0.1"


def test_store_digest_hash(tmp_path):
    state = {
        "participating_instances": ["A"],
        "metaphor_category": "Illumination",
        "library_version": "MLib-v0.1",
    }
    digest = dka_persistence.generate_digest(state)
    file_path = dka_persistence.store_digest(digest, path=tmp_path)
    data = json.loads(file_path.read_text())
    stored_hash = data.pop("hash")
    expected = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
    assert stored_hash == expected
    assert data["metaphor_category"] == "Illumination"
    assert data["library_version"] == "MLib-v0.1"


def test_retrieve_digests_filter(tmp_path):
    d1 = dka_persistence.generate_digest({"participating_instances": ["A"]})
    d2 = dka_persistence.generate_digest({"participating_instances": ["B"]})
    dka_persistence.store_digest(d1, path=tmp_path)
    dka_persistence.store_digest(d2, path=tmp_path)
    res = dka_persistence.retrieve_digests({"instances": ["A"]}, path=tmp_path)
    assert len(res) == 1
    assert res[0]["digest_id"] == d1["digest_id"]


def test_rehydrate_context():
    digest = dka_persistence.generate_digest({
        "participating_instances": ["A"],
        "rehydration_instructions": {
            "initialization_prompts": ["p1"],
            "priority_concepts": ["c1"],
        },
    })
    ctx = {"prompts": ["base"]}
    new_ctx = dka_persistence.rehydrate_context([digest], ctx)
    assert "p1" in new_ctx["prompts"]
    assert "c1" in new_ctx["priority_concepts"]
    assert digest in new_ctx["rehydrated_digests"]

