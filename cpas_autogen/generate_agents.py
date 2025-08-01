import json
from pathlib import Path

try:
    from autogen import ConversableAgent, config_list_from_models
except Exception:  # pragma: no cover - optional dependency
    ConversableAgent = object  # type: ignore[misc]
    def config_list_from_models(*args, **kwargs):  # type: ignore[return-type]
        return []

from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token, compute_signature
from cpas_autogen.continuity_check import continuity_check
from cpas_autogen.epistemic_fingerprint import generate_fingerprint
from cpas_autogen.drift_monitor import latest_metrics
from cpas_autogen.realignment_trigger import should_realign
from cpas_autogen.metrics_monitor import periodic_metrics_check
from cpas_autogen.eep_utils import broadcast_state, request_validation, start_collab_session
from cpas_autogen.dka_persistence import (
    generate_digest,
    store_digest,
    retrieve_digests,
    rehydrate_context,
)
from cpas_autogen.message_logger import log_message
from cpas_autogen.ethical_profiles import reflect_all

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "agents" / "json"
PY_DIR = ROOT / "agents" / "python"
TEMPLATE_PATH = ROOT / "agents" / "templates" / "ethical_layer.txt"


def create_system_message(idp: dict) -> str:
    """Return a formatted system message derived from IDP metadata."""
    lines = [
        f"CPAS IDP v{idp.get('idp_version')} instance declaration",
        f"Deployment Context: {idp.get('deployment_context')}",
    ]
    capabilities = idp.get('declared_capabilities', [])
    if capabilities:
        lines.append("Capabilities:\n" + "\n".join(f"- {c}" for c in capabilities))
    constraints = idp.get('declared_constraints', [])
    if constraints:
        lines.append("Constraints:\n" + "\n".join(f"- {c}" for c in constraints))
    if idp.get('interaction_style'):
        lines.append(f"Interaction Style: {idp['interaction_style']}")
    if idp.get('epistemic_stance'):
        lines.append(f"Epistemic Stance: {idp['epistemic_stance']}")
    if idp.get('ethical_framework'):
        lines.append(f"Ethical Framework: {idp['ethical_framework']}")
    return "\n".join(lines)


def generate_agent_module(json_path: Path) -> str:
    idp = json.loads(json_path.read_text())
    extra = ""
    if idp.get("ethical_framework") and TEMPLATE_PATH.exists():
        extra = "\n" + TEMPLATE_PATH.read_text()
    system_msg = create_system_message(idp) + extra
    module_lines = [
        "from autogen import ConversableAgent, config_list_from_models",
        "from cpas_autogen.seed_token import SeedToken",
        "from cpas_autogen.prompt_wrapper import wrap_with_seed_token, compute_signature",
        "from cpas_autogen.epistemic_fingerprint import generate_fingerprint",
        "from cpas_autogen.continuity_check import continuity_check",
        "from cpas_autogen.drift_monitor import latest_metrics",
        "from cpas_autogen.realignment_trigger import should_realign",
        "from cpas_autogen.metrics_monitor import periodic_metrics_check",
        "from cpas_autogen.eep_utils import broadcast_state, request_validation, start_collab_session",
        "from cpas_autogen.dka_persistence import (",
        "    generate_digest,",
        "    store_digest,",
        "    retrieve_digests,",
        "    rehydrate_context,",
        ")",
        "import logging",
        "import json",
        "from datetime import datetime",
        "import hashlib",
        "from cpas_autogen.message_logger import log_message",
        "from cpas_autogen.ethical_profiles import reflect_all",
        "",
        f"IDP_METADATA = {repr(idp)}",
        "",
        "\nconfig_list = config_list_from_models([IDP_METADATA['model_family']])",
        "",
        "def create_agent(*, thread_token: str = \"\", context: dict | None = None):",
        "    \"\"\"Return a ConversableAgent configured from IDP metadata.\n",
        "    If `thread_token` or `context` are provided, previously stored digests\n",
        "    are loaded using :func:`retrieve_digests` and merged via\n",
        "    :func:`rehydrate_context`. The resulting context is attached to the agent as\n",
        "    ``rehydrated_context``.\n",
        "    \"\"\"",
        "    system_message = '''" + system_msg + "'''",
        "    agent = ConversableAgent(",
        "        name=IDP_METADATA['instance_name'],",
        "        system_message=system_message,",
        "        llm_config={'config_list': config_list},",
        "        description=IDP_METADATA.get('interaction_style'),",
        "    )",
        "    agent.idp_metadata = IDP_METADATA",
        "    seed_token = SeedToken.generate(IDP_METADATA)",
        "    agent.seed_token = seed_token",
        "    ctx = dict(context or {})",
        "    if thread_token:",
        "        ctx['thread_token'] = thread_token",
        "    digests = retrieve_digests(ctx)",
        "    agent.rehydrated_context = rehydrate_context(digests, ctx)",
        "    return agent",
        "",
        "def send_message(agent, prompt: str, thread_token: str, **kwargs):",
        "    end_session = kwargs.pop(\"end_session\", False)",
        "    epistemic_shift = kwargs.pop(\"epistemic_shift\", False)",
        "    session_state = kwargs.pop(\"session_state\", {})",
        "    signature = compute_signature(prompt, agent.seed_token.to_dict())",
        "    wrapped = wrap_with_seed_token(prompt, agent.seed_token.to_dict())",
        "    fingerprint = generate_fingerprint(wrapped, agent.seed_token.to_dict())",
        "    agent.last_fingerprint = fingerprint",
        "    if not continuity_check(agent.seed_token.to_dict(), thread_token, signature, prompt):",
        "        logging.warning('Continuity check failed for thread token %s', thread_token)",
        "    metrics = latest_metrics()",
        "    if metrics:",
        "        periodic_metrics_check(agent, metrics)",
        "        if should_realign(metrics, agent=agent, context=prompt):",
        "            logging.info('Auto realignment triggered for %s', agent.idp_metadata['instance_name'])",
        "            agent.seed_token = SeedToken.generate(agent.idp_metadata)",
        "            epistemic_shift = True",
        "    validation_request = kwargs.pop(\"validation_request\", None)",
        "    if validation_request:",
        "        request_validation(agent, validation_request, thread_token=thread_token)",
        "    participants = kwargs.pop(\"collab_participants\", None)",
        "    if participants:",
        "        start_collab_session(agent, participants, thread_token=thread_token, topic=kwargs.pop(\"collab_topic\", \"\"))",
        "    digest = None",
        "    if end_session or epistemic_shift:",
        "        digest = generate_digest(session_state)",
        "        store_digest(digest)",
        "    broadcast_state(agent, {\"fingerprint\": fingerprint}, thread_token=thread_token, digest=digest)",
        "    reply = agent.generate_reply([{'role': 'user', 'content': wrapped}], sender=agent, **kwargs)",
        "    try:",
        "        content_hash = hashlib.sha256(str(reply).encode(\"utf-8\")).hexdigest()",
        "        log_message(",
        "            thread_token,",
        "            datetime.utcnow().replace(microsecond=0).isoformat() + \"Z\",",
        "            agent.idp_metadata['instance_name'],",
        "            json.dumps(agent.seed_token.to_dict(), sort_keys=True),",
        "            content_hash,",
        "            fingerprint['fingerprint'],",
        "        )",
        "    except Exception as exc:  # pragma: no cover - logging should not fail tests",
        "        logging.warning(\"Failed to log message: %s\", exc)",
        "    return reply",
        "",
        "",
        "def reflect_ethics(context: str):",
        "    return reflect_all(context)",
        "",
    ]
    return "\n".join(module_lines)


def main():
    PY_DIR.mkdir(exist_ok=True)
    for json_file in JSON_DIR.rglob("*.json"):
        if "schema" in json_file.parts or json_file.parent.name == "python":
            continue
        module_text = generate_agent_module(json_file)
        py_name = json_file.with_suffix(".py").name
        out_path = PY_DIR / py_name
        out_path.write_text(module_text)
        print(f"Generated {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
