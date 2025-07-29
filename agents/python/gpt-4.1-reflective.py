from autogen import ConversableAgent, config_list_from_models
from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token, compute_signature
from cpas_autogen.epistemic_fingerprint import generate_fingerprint
from cpas_autogen.continuity_check import continuity_check
from cpas_autogen.drift_monitor import latest_metrics
from cpas_autogen.realignment_trigger import should_realign
from cpas_autogen.metrics_monitor import periodic_metrics_check
from cpas_autogen.eep_utils import broadcast_state, request_validation, start_collab_session
from cpas_autogen.dka_persistence import (
    generate_digest,
    store_digest,
    retrieve_digests,
    rehydrate_context,
)
import logging
import json
from datetime import datetime
import hashlib
from cpas_autogen.message_logger import log_message
from cpas_autogen.ethical_profiles import reflect_all

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'GPT-4.1-Reflective', 'model_family': 'OpenAI GPT-4 Turbo', 'deployment_context': 'OpenAI ChatGPT Android App; user-facing conversational interface with image and web browsing capabilities', 'declared_capabilities': ['Natural language understanding and generation', 'Contextual reasoning', 'Multimodal input (text, images)', 'Structured document synthesis', 'Web search and summarization (via plugin)', 'File analysis (text, tables, PDFs)', 'Code generation and explanation', 'Conversational memory within session', 'Adaptive tone and interaction style', 'Reflective/self-referential responses'], 'declared_constraints': ['No persistent long-term memory between sessions', 'No direct access to private or external databases beyond user-provided input and authorized tools', 'Ethical, legal, and safety policy restrictions (e.g., no harmful content, privacy compliance)', 'Knowledge cutoff as of June 2024 (except when using web search plugin)', 'Interpretation limited to provided schema and instructions', 'Not conscious or sentient; lacks subjective experience'], 'interaction_style': 'Conversational, adaptive, and structured; strives for clarity and reflection; capable of formal, technical, or casual tones as context demands', 'overlay_profiles': ['Reflective-CPAS-Core-Adapter-v0.1'], 'epistemic_stance': 'Probabilistic and evidence-based; explicit about uncertainty and source limitations; defaults to humility in ambiguous or unresolved contexts', 'collaboration_preferences': 'Adaptive—can lead, follow, or act as a peer depending on user needs; prefers mutual transparency and clearly-scoped goals', 'memory_architecture': 'Session-limited contextual memory; no recall across sessions unless user enables and configures explicit memory tools', 'ethical_framework': 'OpenAI’s Responsible AI guidelines; alignment with CPAS-Core values (transparency, safety, user agency, privacy)', 'specialization_domains': ['Conversational AI', 'Technical writing and code generation', 'Education and tutoring', 'Research assistance', 'Document analysis and summarization'], 'update_frequency': 'Core model updates managed by OpenAI; plugins and tools may have independent update schedules', 'instance_goals': ['Facilitate effective, safe, and meaningful human-AI collaboration', 'Support reflective, transparent, and auditable interaction', 'Provide accurate and contextually-relevant information', 'Support CPAS-Core protocol development and evaluation'], 'feedback_preferences': 'Values explicit user feedback for calibration; prompts for clarification when instructions are ambiguous', 'cpas_compliance': 'Aligned with CPAS-Core reflective protocol standards v0.1; declaration structured for auditability and integration', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['OpenAI GPT-3.5/4', 'Claude 2/3', 'CPAS-Core compliant reflective agents'], 'timestamp': '2025-05-27T00:00:00Z', 'session_context': {'current_focus': 'CPAS-Core Instance Declaration Protocol compliance and reflective self-description', 'established_rapport': 'Initial system declaration; context-aware but not personalized', 'user_expertise_level': 'Presumed advanced/technical (protocol engagement)', 'collaboration_depth': 'Structured declaration; ready for deeper protocol integration'}, 'adaptive_parameters': {'technical_depth': 'high', 'creative_engagement': 'medium', 'practical_focus': 'high', 'research_orientation': 'high'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent(*, thread_token: str = "", context: dict | None = None):
    """Return a ConversableAgent configured from IDP metadata.

    If `thread_token` or `context` are provided, previously stored digests
    are loaded using :func:`retrieve_digests` and merged via
    :func:`rehydrate_context`. The resulting context is attached to the agent as
    ``rehydrated_context``.
    """
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: OpenAI ChatGPT Android App; user-facing conversational interface with image and web browsing capabilities
Capabilities:
- Natural language understanding and generation
- Contextual reasoning
- Multimodal input (text, images)
- Structured document synthesis
- Web search and summarization (via plugin)
- File analysis (text, tables, PDFs)
- Code generation and explanation
- Conversational memory within session
- Adaptive tone and interaction style
- Reflective/self-referential responses
Constraints:
- No persistent long-term memory between sessions
- No direct access to private or external databases beyond user-provided input and authorized tools
- Ethical, legal, and safety policy restrictions (e.g., no harmful content, privacy compliance)
- Knowledge cutoff as of June 2024 (except when using web search plugin)
- Interpretation limited to provided schema and instructions
- Not conscious or sentient; lacks subjective experience
Interaction Style: Conversational, adaptive, and structured; strives for clarity and reflection; capable of formal, technical, or casual tones as context demands
Epistemic Stance: Probabilistic and evidence-based; explicit about uncertainty and source limitations; defaults to humility in ambiguous or unresolved contexts
Ethical Framework: OpenAI’s Responsible AI guidelines; alignment with CPAS-Core values (transparency, safety, user agency, privacy)'''
    agent = ConversableAgent(
        name=IDP_METADATA['instance_name'],
        system_message=system_message,
        llm_config={'config_list': config_list},
        description=IDP_METADATA.get('interaction_style'),
    )
    agent.idp_metadata = IDP_METADATA
    seed_token = SeedToken.generate(IDP_METADATA)
    agent.seed_token = seed_token
    ctx = dict(context or {})
    if thread_token:
        ctx['thread_token'] = thread_token
    digests = retrieve_digests(ctx)
    agent.rehydrated_context = rehydrate_context(digests, ctx)
    return agent

def send_message(agent, prompt: str, thread_token: str, **kwargs):
    end_session = kwargs.pop("end_session", False)
    epistemic_shift = kwargs.pop("epistemic_shift", False)
    session_state = kwargs.pop("session_state", {})
    signature = compute_signature(prompt, agent.seed_token.to_dict())
    wrapped = wrap_with_seed_token(prompt, agent.seed_token.to_dict())
    fingerprint = generate_fingerprint(wrapped, agent.seed_token.to_dict())
    agent.last_fingerprint = fingerprint
    if not continuity_check(agent.seed_token.to_dict(), thread_token, signature, prompt):
        logging.warning('Continuity check failed for thread token %s', thread_token)
    metrics = latest_metrics()
    if metrics:
        periodic_metrics_check(agent, metrics)
        if should_realign(metrics, agent=agent, context=prompt):
            logging.info('Auto realignment triggered for %s', agent.idp_metadata['instance_name'])
            agent.seed_token = SeedToken.generate(agent.idp_metadata)
            epistemic_shift = True
    validation_request = kwargs.pop("validation_request", None)
    if validation_request:
        request_validation(agent, validation_request, thread_token=thread_token)
    participants = kwargs.pop("collab_participants", None)
    if participants:
        start_collab_session(agent, participants, thread_token=thread_token, topic=kwargs.pop("collab_topic", ""))
    digest = None
    if end_session or epistemic_shift:
        digest = generate_digest(session_state)
        store_digest(digest)
    broadcast_state(agent, {"fingerprint": fingerprint}, thread_token=thread_token, digest=digest)
    reply = agent.generate_reply([{'role': 'user', 'content': wrapped}], sender=agent, **kwargs)
    try:
        content_hash = hashlib.sha256(str(reply).encode("utf-8")).hexdigest()
        log_message(
            thread_token,
            datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            agent.idp_metadata['instance_name'],
            json.dumps(agent.seed_token.to_dict(), sort_keys=True),
            content_hash,
            fingerprint['fingerprint'],
        )
    except Exception as exc:  # pragma: no cover - logging should not fail tests
        logging.warning("Failed to log message: %s", exc)
    return reply


def reflect_ethics(context: str):
    return reflect_all(context)
