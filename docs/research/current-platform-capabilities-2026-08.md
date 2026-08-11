# Current AI platform capability ledger

**Research cut-off:** 2026-08-11

**Purpose:** distinguish current documented platform features from historical
CPAS claims and from the CPAS v2 proposal.

Only first-party vendor documentation and protocol specifications are used for
platform claims. Availability, limits, and product names can change; adapters
must probe the deployed environment rather than infer capability from this
document.

## Findings

| Area | Current primary documentation | What is actually supported | CPAS v2 implication |
|---|---|---|---|
| API conversation state | OpenAI [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) | APIs can carry state through prior response references or explicit conversation objects. Retention and application behavior remain product/API concerns. | Contextual continuity may be supplied by a platform, but must not be labeled durable CPAS state unless retention and retrieval are verified. |
| Structured output | OpenAI [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), Google [Structured output](https://ai.google.dev/gemini-api/docs/structured-output), Anthropic [tool definitions](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use) | Major runtimes accept JSON-schema-like response or tool contracts, with provider-specific subsets and failure modes. | Use provider-neutral canonical schemas plus adapter tests. A schema request does not guarantee semantic truth. |
| Agents and tools | OpenAI [Agents](https://developers.openai.com/api/docs/guides/agents), Anthropic [Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview), Google [ADK](https://google.github.io/adk-docs/) | Current platforms can orchestrate model calls, tools, files, subagents, and control flow. Tool sets and permission models differ. | Runtime adapters declare and probe tools. CPAS identity does not inherit the identity or authority of an orchestrator. |
| Private reasoning boundary | OpenAI [Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices) | Reasoning models support useful explanations and summaries, but prompting for hidden chain-of-thought is neither a portable nor necessary interface. | RRL requires epistemic summaries—assumptions, evidence, uncertainty, alternatives, criteria—not unrestricted private traces. |
| Model selection and replacement | OpenAI [Model selection](https://developers.openai.com/api/docs/guides/model-selection), Google ADK [Models](https://google.github.io/adk-docs/agents/models/) | Applications choose or route among changing model catalogs; orchestration frameworks can abstract model providers. | Runtime bindings are versioned observations. Rebinding requires capability validation, not an identity rewrite. |
| Chat projects/workspaces | OpenAI Help [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt), Anthropic Help [Claude Projects](https://support.anthropic.com/en/articles/9517075-what-are-projects) | Project features can group chats, instructions, and uploaded knowledge; product-specific memory and retrieval behavior varies. | Declare project/workspace state separately from model context and externally persisted CPAS state. Do not promise portability. |
| Custom assistants | OpenAI Help [GPTs in ChatGPT](https://help.openai.com/en/articles/8554407-gpts-in-chatgpt), [Creating and editing GPTs](https://help.openai.com/en/articles/8554397-creating-and-editing-gpts) | Configured assistants can combine instructions, knowledge, and capabilities, but product configurations and chats have distinct persistence semantics. | An IDP can configure a custom assistant, but the assistant container is a deployment binding, not the instance identity itself. |
| Long-term memory and sessions | Google ADK [Sessions and memory](https://google.github.io/adk-docs/sessions/), Anthropic Agent SDK [Sessions](https://platform.claude.com/docs/en/agent-sdk/sessions) | Agent frameworks distinguish active session context/state from resumable or long-term stores. In-memory services are explicitly non-persistent; managed/database-backed services persist. | CPAS must report four state layers and four continuity forms. “Memory available” is too coarse. |
| Artifacts and files | Google ADK [Artifacts](https://google.github.io/adk-docs/artifacts/), OpenAI [File inputs](https://developers.openai.com/api/docs/guides/pdf-files), Anthropic Agent SDK [Overview](https://platform.claude.com/docs/en/agent-sdk/overview) | Files and generated artifacts can be passed to or managed by agent systems, subject to storage, type, size, and permission limits. | Declare artifact access and provenance. Content retrieved from a file/store is data, not automatically trusted instruction. |
| Function/tool calling | OpenAI [Function calling](https://developers.openai.com/api/docs/guides/function-calling), Google [Function calling](https://ai.google.dev/gemini-api/docs/function-calling), Anthropic [Tool use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) | Models can propose typed calls; the host executes tools and returns results. The host remains responsible for validation and authorization. | Capability negotiation describes callable contracts. IDP/SeedToken never grants tool authorization. |
| MCP | Model Context Protocol [Specification](https://modelcontextprotocol.io/specification/2025-11-25), Anthropic [MCP connector](https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector) | MCP defines lifecycle initialization, capability negotiation, tools/resources/prompts, and optional authorization mechanisms. Implementations support different subsets. | MCP is a suitable adapter boundary, not a replacement for EEP. EEP conveys epistemic records; MCP discovers/invokes capabilities. |
| Agent state serialization | Microsoft AutoGen [Save and load agent state](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html), Microsoft [Agent Framework migration guide](https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/) | Agent frameworks can serialize team/agent state, with framework-specific compatibility and migration constraints. | A runtime checkpoint is a fifth implementation artifact, but does not replace portable DKA/IDP state. Record framework/version provenance. |
| External knowledge/RAG | OpenAI [Retrieval](https://developers.openai.com/api/docs/guides/retrieval), Google [File Search](https://ai.google.dev/gemini-api/docs/file-search), Anthropic Help [Project knowledge](https://support.anthropic.com/en/articles/9517075-what-are-projects) | Platforms offer hosted retrieval over uploaded/external knowledge. Retrieval indexes are lossy/derived views and may be service-bound. | Canonical DKA-E records live outside embeddings. Vector stores are rebuildable retrieval indexes with source links and model metadata. |
| Repository integration | GitHub [Git database REST API](https://docs.github.com/en/rest/git), OpenAI [Codex cloud environments](https://developers.openai.com/codex/cloud/environments) | Git provides versioned blobs, trees, commits, refs, and review workflows; coding agents can operate in configured repositories/environments. | Git is one DKA-E backend and strong provenance surface, but repository write authority remains external to CPAS. |

## Required state distinction

CPAS v2 uses four non-interchangeable state layers:

| Layer | Typical contents | Durability claim |
|---|---|---|
| **Model context** | Current prompt, messages, tool results, retrieved excerpts | Available only for the active inference/context unless the host stores it. |
| **Platform memory** | Product-managed remembered preferences or conversation state | Provider/product-specific; declare availability, scope, retention, and user controls when known. |
| **Project/workspace state** | Files, repository checkout, project instructions, artifacts | Survives according to workspace policy; portability and visibility are environment-specific. |
| **Externally persisted CPAS state** | Versioned IDPs, DKAs, events, continuity tokens, provenance | Durable only when a configured external store successfully writes and can later retrieve/verify it. |

An implementation may expose all, some, or none. Rehydration reports the layer
from which each item came.

## Capability status model

Every runtime capability is labeled:

- `unknown`: no reliable information;
- `declared`: configuration/vendor metadata says it is present;
- `probed`: a bounded availability check succeeded;
- `verified`: the task-relevant behavior passed a recorded test;
- `unavailable`: absent, denied, or failed.

The status is accompanied by `checked_at`, method/evidence, and constraints.
This avoids converting a current documentation claim into a guarantee about a
particular deployment.

## What the historical corpus did and did not anticipate

The historical CPAS corpus explicitly anticipated modular deployment,
cross-instance exchange, externalized DKA-E continuity, evolving anchors, and
metadata-assisted reconstruction. Those are genuine conceptual predecessors.
It did **not** specify the contemporary vendor APIs, MCP lifecycle, current
structured-output dialects, managed project memory semantics, or security
properties required to deploy them. CPAS v2 maps current mechanisms onto the
earlier concepts; it does not attribute those later mechanisms to v1.1.

## Research limitations

- Product documentation is not proof that a capability is enabled for a given
  account, region, model, or deployment.
- Hosted memory and retention behavior can change independently of CPAS.
- Provider structured-output subsets differ and require conformance tests.
- The documentation set is a dated snapshot. Runtime adapters must refresh and
  validate capabilities rather than treating this ledger as discovery.

**Confidence: High** that the linked documents support the broad capability
distinctions; **Medium** that any named hosted feature retains identical
semantics after the research cut-off.
