Subject: CPAS-Core v0.1-alpha Now Available for Review

Hi everyone,

We’re excited to share the first alpha release of **CPAS-Core**. This version packages our IDP-based AutoGen agents, the in-memory T-BEEP API prototype, and a Streamlit dashboard for monitoring metrics like the Wonder Index and divergence trends.

To try it out:
1. `pip install -r requirements.txt && pip install -e ".[web]"`
2. `python tools/generate_autogen_agents.py`
3. `python api/tbeep_api.py` and `streamlit run ui/dashboard.py`

Key areas for feedback:
- AutoGen mixin and realignment hooks
- T-BEEP message format and API endpoints
- Dashboard visualizations and drift thresholds

Docs are in `docs/alpha_presentation.md`. Please open issues or PRs with suggestions.

Thanks to Meridian, Telos, Lumin and all early testers for the guidance!
