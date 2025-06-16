import json
from pathlib import Path
from textwrap import indent

from autogen import ConversableAgent, config_list_from_models

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "instances"
PY_DIR = JSON_DIR / "python"


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
        "",
        f"IDP_METADATA = {json.dumps(idp, indent=2)}",
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
        "    return agent",
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
