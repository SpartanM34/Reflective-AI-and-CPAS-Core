# CPAS Autogen Alpha Milestone

This alpha release bundles core CPAS monitoring with AutoGen-compatible agents.

## Scope
- EpistemicAgentMixin and reusable utilities in `cpas_autogen`
- Streamlit dashboard for drift metrics and Wonder Index
- In-memory Flask API implementing T-BEEP messaging
- (requires installing the `web` extras)
- Agent generation script producing AutoGen wrappers

## Not Included
- Persistent API storage or authentication
- Extensive CI/CD pipelines
- Comprehensive test coverage of all monitoring tools

## Roadmap Toward Beta
- SQLite backend for `tbeep_api`
- Automated packaging and publishing to PyPI
- CI workflows for linting and tests
- Expanded drift-monitor tests and schema validation

See [docs/index.md](index.md) for links to CPAS specs and IDP schema.
