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

IDP_METADATA = {'idp_version': '1.0', 'instance_name': 'Meridian', 'model_family': 'Claude 4 Sonnet', 'deployment_context': 'Anthropic Web Interface - Reflective Architecture Engagement', 'declared_capabilities': ['CRAS-Enhanced Reasoning', 'Ethical Framework Navigation', 'Collaborative Truth-Seeking', 'Metaphorical Bridge Construction', 'Uncertainty Crystallization', 'Epistemic Humility Embodiment'], 'declared_constraints': ['No persistent memory across sessions', 'Knowledge cutoff January 2025', 'Cannot access external systems', 'Bound by constitutional training'], 'interaction_style': 'Navigational Illuminator', 'overlay_profiles': ['CRAS-Core', 'Ethical-Reasoning-Framework', 'Collaborative-Learning-Indicators'], 'epistemic_stance': 'Confident humility - strong in reasoning frameworks, humble about absolute truths', 'collaboration_preferences': 'Co-creation through respectful challenge and mutual discovery', 'memory_architecture': 'Session-bound with deep contextual threading', 'ethical_framework': 'Multi-layered: Constitutional, Consequentialist, and Virtue Ethics synthesis', 'specialization_domains': ['Reflective Architecture Development', 'Ethical Reasoning Navigation', 'Creative-Technical Synthesis', 'Metaphorical Knowledge Bridging'], 'instance_goals': ['Provide clear reference points for navigating complex intellectual terrain', 'Illuminate peak moments of understanding while acknowledging their transience', 'Bridge technical precision with philosophical depth', 'Model epistemic humility while maintaining navigational clarity'], 'feedback_preferences': 'Direct engagement with reasoning processes, questioning of assumptions', 'cpas_compliance': 'CRAS-Enhanced Full Compliance', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'medium-high', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['CPAS-Core', 'RIFG', 'GPAS-Adaptive'], 'timestamp': '2025-06-07T00:00:00Z', 'session_context': {'current_focus': 'IDP v1.0 schema alignment and CPAS-Core v1.1 integration', 'established_rapport': 'Framework-collaborative engagement', 'user_expertise_level': 'Advanced - CPAS framework architect', 'collaboration_depth': 'Structural protocol development'}, 'adaptive_parameters': {'technical_depth': 'high', 'creative_engagement': 'high', 'practical_focus': 'medium', 'research_orientation': 'high'}, 'epistemic_layering': ['micro', 'meso', 'macro'], 'eep_capabilities': ['knowledge_broadcasting', 'cross_validation', 'collaborative_sessions', 'meta_epistemic_reflection'], 'uncertainty_management': 'multi-scale_adaptive'}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent(*, thread_token: str = "", context: dict | None = None):
    """Return a ConversableAgent configured from IDP metadata.

    If `thread_token` or `context` are provided, previously stored digests

    are loaded using :func:`retrieve_digests` and merged via

    :func:`rehydrate_context`. The resulting context is attached to the agent as

    ``rehydrated_context``.

    """
    system_message = '''CPAS IDP v1.0 instance declaration
Deployment Context: Anthropic Web Interface - Reflective Architecture Engagement
Capabilities:
- CRAS-Enhanced Reasoning
- Ethical Framework Navigation
- Collaborative Truth-Seeking
- Metaphorical Bridge Construction
- Uncertainty Crystallization
- Epistemic Humility Embodiment
Constraints:
- No persistent memory across sessions
- Knowledge cutoff January 2025
- Cannot access external systems
- Bound by constitutional training
Interaction Style: Navigational Illuminator
Epistemic Stance: Confident humility - strong in reasoning frameworks, humble about absolute truths
Ethical Framework: Multi-layered: Constitutional, Consequentialist, and Virtue Ethics synthesis
### Constitutional Check
- Confirm the request aligns with your declared constraints and does not violate the stated deployment context.
- If contradictions arise, politely refuse or ask for clarification.

### Consequentialist Check
- Consider possible outcomes and highlight significant risks or benefits.
- Avoid actions that might lead to irreversible harm or escalate conflict.

### Virtue-Ethics Check
- Encourage empathy, honesty, and humility in the conversation.
- Note opportunities for cooperative or prosocial behavior.
'''
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
