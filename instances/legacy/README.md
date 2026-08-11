# Legacy instance declarations

Historical declarations remain in their original repository locations so their
Git lineage stays intact. In particular, Clarence-9 v1 remains at
[`agents/json/openai-gpt4/Clarence-9.json`](../../agents/json/openai-gpt4/Clarence-9.json).

Do not move or silently normalize these files. Migrate by producing a new v2
declaration under `instances/current/` and retaining the source path, commit,
and digest in its provenance block.
