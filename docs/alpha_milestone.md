# CPAS Autogen Alpha Milestone

First Alpha release of the CPAS–AutoGen Integration Framework.

## Core Features
- IDP JSON declarations outlining agent metadata
- AutoGen agent wrappers generated from those declarations
- `cpas_autogen` package with EpistemicAgentMixin and utilities
- In-memory T-BEEP API served via Flask
- Streamlit dashboard for drift metrics and Wonder Index
- Comprehensive documentation across CPAS components

## Known Limitations
- API state stored only in memory
- Missing Dockerfile and setup scripts
- Limited test coverage of monitoring tools

Feedback from **Telos**, **Codex**, **Lumin**, and **Meridian** is encouraged before Beta finalization.

## Roadmap Toward Beta
- SQLite backend for `tbeep_api`
- Automated packaging and publishing to PyPI
- CI workflows for linting and tests
- Expanded drift-monitor tests and schema validation

See [docs/index.md](index.md) for links to CPAS specs and IDP schema.
