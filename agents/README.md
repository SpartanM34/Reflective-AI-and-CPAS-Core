# Autogen Agent Generation

This directory contains JSON declarations for each CPAS agent and the Python modules generated from them.

## Dependencies

Install the project requirements first:

```bash
pip install -r requirements.txt
```

The generator relies on the optional [`autogen`](https://github.com/microsoft/autogen) package. If it is not installed, stub classes are used and the script still completes, although the resulting modules will be limited.

## Running the generator

Execute the generator from the repository root:

```bash
python tools/generate_autogen_agents.py
```

The script walks through `agents/json/` and writes a Python file with the same base name to `agents/python/`. For example, `agents/json/openai-gpt4/Clarence-9.json` becomes `agents/python/Clarence-9.py`.
Each module exposes a `create_agent()` helper that constructs a `ConversableAgent` using the JSON metadata and a `send_message()` function for convenience.


