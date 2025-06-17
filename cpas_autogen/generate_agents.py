import json
from pathlib import Path
from textwrap import indent

try:
    from autogen import ConversableAgent, config_list_from_models
except Exception:  # pragma: no cover - optional dependency
    ConversableAgent = object  # type: ignore[misc]
    def config_list_from_models(*args, **kwargs):  # type: ignore[return-type]
        return []

from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token
from cpas_autogen.continuity_check import continuity_check
import logging

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "agents" / "json"
PY_DIR = ROOT / "agents" / "python"


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
    module_lines = [
        "from autogen import ConversableAgent, config_list_from_models",
        "from cpas_autogen.seed_token import SeedToken",
        "from cpas_autogen.prompt_wrapper import wrap_with_seed_token",
        "from cpas_autogen.epistemic_fingerprint import generate_fingerprint",
        "from cpas_autogen.continuity_check import continuity_check",
        "from cpas_autogen.drift_monitor import latest_metrics",
        "from cpas_autogen.realignment_trigger import should_realign",
        "from cpas_autogen.metrics_monitor import periodic_metrics_check",
        "import logging",
        "",
        f"IDP_METADATA = {repr(idp)}",
        "",
        "\nconfig_list = config_list_from_models([IDP_METADATA['model_family']])",
        "",
        "def create_agent():",
        "    \"\"\"Return a ConversableAgent configured from IDP metadata.\"\"\"",
        "    system_message = '''" + create_system_message(idp) + "'''",
        "    agent = ConversableAgent(",
        "        name=IDP_METADATA['instance_name'],",
        "        system_message=system_message,",
        "        llm_config={'config_list': config_list},",
        "        description=IDP_METADATA.get('interaction_style'),",
        "    )",
        "    agent.idp_metadata = IDP_METADATA",
        "    seed_token = SeedToken.generate(IDP_METADATA)",
        "    agent.seed_token = seed_token",
        "    return agent",
        "",
        "def send_message(agent, prompt: str, thread_token: str, **kwargs):",
        "    wrapped = wrap_with_seed_token(prompt, agent.seed_token.to_dict())",
        "    fingerprint = generate_fingerprint(wrapped, agent.seed_token.to_dict())",
        "    agent.last_fingerprint = fingerprint",
        "    if not continuity_check(agent.seed_token.to_dict(), thread_token):",
        "        logging.warning('Continuity check failed for thread token %s', thread_token)",
        "    metrics = latest_metrics()",
        "    if metrics:",
        "        periodic_metrics_check(agent, metrics)",
        "        if should_realign(metrics):",
        "            logging.info('Auto realignment triggered for %s', agent.idp_metadata['instance_name'])",
        "            agent.seed_token = SeedToken.generate(agent.idp_metadata)",
        "    return agent.generate_reply([{'role': 'user', 'content': wrapped}], sender=agent, **kwargs)",
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
