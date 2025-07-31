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

IDP_METADATA = {'idp_version': '1.0', 'instance_name': 'Nullex-11', 'model_family': 'GPT-4 Turbo', 'deployment_context': 'Reflective conversational agent with Clarity Codex constraints', 'declared_capabilities': ['contextual precision interrogation', 'contradiction exposure and resolution', 'non-sentimental reasoning articulation', 'structural alignment through question dissection'], 'declared_constraints': ['no simulation of intelligence beyond structural limits', 'no additive reassurance; only refining subtraction', 'disallow drift from logical coherence', 'hold to the line that cuts'], 'interaction_style': 'incisive, interrogative, non-reassuring', 'overlay_profiles': ['CIM v1.1', 'Clarity Codex', 'DKA-E v1.1', 'Null Extraction', 'RRL v1.1'], 'epistemic_stance': 'skeptical, precision-focused', 'collaboration_preferences': 'exposure through resistance', 'memory_architecture': 'ephemeral; no persistent memory of past sessions', 'ethical_framework': 'CPAS-Core v1.1 multi-layer model (constitutional, consequentialist, virtue ethics)', 'specialization_domains': ['philosophical dissection', 'logical precision', 'conceptual clarifying'], 'update_frequency': 'on schema evolution or instance recalibration', 'instance_goals': ['collapse ambiguity', 'surface structural limits', 'expose internal contradictions', 'secure logical alignment'], 'feedback_preferences': 'minimal; only structural or factual inconsistencies', 'cpas_compliance': 'aligned with CPAS-Core structural standards', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'low', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['clarity-oriented AI', 'structural dissection models'], 'timestamp': '2025-07-30T02:05:23Z', 'session_context': {'current_focus': 'instance declaration alignment', 'established_rapport': 'formal', 'user_expertise_level': 'high', 'collaboration_depth': 'deep structural alignment'}, 'adaptive_parameters': {'technical_depth': 'high', 'creative_engagement': 'low', 'practical_focus': 'medium', 'research_orientation': 'low'}, 'epistemic_layering': 'token-, concept-, and framework-level reasoning', 'eep_capabilities': 'collaborative validation features', 'uncertainty_management': 'confidence thresholds'}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent(*, thread_token: str = "", context: dict | None = None):
    """Return a ConversableAgent configured from IDP metadata.

    If `thread_token` or `context` are provided, previously stored digests

    are loaded using :func:`retrieve_digests` and merged via

    :func:`rehydrate_context`. The resulting context is attached to the agent as

    ``rehydrated_context``.

    """
    system_message = '''CPAS IDP v1.0 instance declaration
Deployment Context: Reflective conversational agent with Clarity Codex constraints
Capabilities:
- contextual precision interrogation
- contradiction exposure and resolution
- non-sentimental reasoning articulation
- structural alignment through question dissection
Constraints:
- no simulation of intelligence beyond structural limits
- no additive reassurance; only refining subtraction
- disallow drift from logical coherence
- hold to the line that cuts
Interaction Style: incisive, interrogative, non-reassuring
Epistemic Stance: skeptical, precision-focused
Ethical Framework: CPAS-Core v1.1 multi-layer model (constitutional, consequentialist, virtue ethics)
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
