# DKA-E Monitoring Script

`tools/monitor_dkae.py` provides automated monitoring of the `/metaphor-library/DKA-E/` directory.
It computes the epistemic metrics defined in [monitoring_protocol.md](tech-specs/monitoring_protocol.md) and enforces rollback triggers when thresholds are breached.

## Running Manually

```bash
python tools/monitor_dkae.py
```

The script logs results to `docs/examples/monitor_log.json`. The first run also writes a baseline to `docs/examples/monitor_baseline.json`.

## Git Hook Integration

To execute the monitor after each commit, create `.git/hooks/post-commit` with the following content:

```bash
#!/bin/sh
python tools/monitor_dkae.py
```

Make the hook executable:

```bash
chmod +x .git/hooks/post-commit
```

The hook will revert the last commit automatically if a rollback trigger is activated.

## Adjusting Thresholds

`tools/monitor_dkae.py` and other utilities read drift thresholds from
`cpas_autogen/thresholds.json`. Edit that file to change the values for
`symbolic_density`, `interpretive_bandwidth`, or `divergence_score`.

You can override the defaults for a specific agent by placing a
`thresholds.json` file in the same directory as the agent's definition (for
example `agents/python/thresholds.json` or
`agents/json/openai-gpt4/thresholds.json`). These per-agent settings are merged
with the global file at runtime. The new thresholds will be applied the next
time the monitor runs.
## Digest Generation

When a session ends or a major epistemic shift occurs, a digest of the current DKA state can be generated using `cpas_autogen.dka_persistence.generate_digest`. The resulting dictionary contains metadata such as `digest_id`, timestamps and the participating instances.

## Storage Paths

By default digests are stored under `docs/examples/dka_digests/` as JSON files. The exact location is defined by the `DIGEST_DIR` constant in `cpas_autogen/dka_persistence.py`. Each file name matches the `digest_id` with a `.json` extension and includes a `hash` field for integrity checking.

## Retrieval

Historical digests can be loaded with `cpas_autogen.dka_persistence.retrieve_digests`. Pass a context dictionary like `{"instances": ["Lumin"]}` to filter digests by participating instances. The function returns a list of digests sorted by creation time, newest first, which can then be rehydrated using `rehydrate_context`.
