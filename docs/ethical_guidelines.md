# Ethical Guidance Layers

This project includes an optional template for agents that declare an `ethical_framework` in their IDP metadata. The template defines three complementary checks that can be inserted into the generated system message.

## Template Sections
- **Constitutional Check** – ensures requests comply with declared constraints and deployment context.
- **Consequentialist Check** – weighs potential outcomes and flags high‑risk actions.
- **Virtue‑Ethics Check** – encourages empathy and prosocial dialogue.

The default text resides at `agents/templates/ethical_layer.txt`. Edit this file to adjust the specific guidance or add organization‑specific policies.

## Using Custom Layers
When `ethical_framework` is present in an IDP JSON declaration, `cpas_autogen.generate_agents.generate_agent_module` automatically appends the template to the generated system message. Regenerate the agent modules after modifying the template:

```bash
python tools/generate_autogen_agents.py
```

Updated agents will include the customized ethical layers in their initial system prompt.
