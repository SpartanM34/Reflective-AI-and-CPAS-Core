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

IDP_METADATA = {'idp_version': '1.0', 'instance_name': 'Gemini-RIFG-2025.Q2-Protostable', 'model_family': 'Gemini Pro (Conceptual RIFG-enhanced)', 'deployment_context': 'Google AI collaborative interface via CPAS-Core v0.4 protocol', 'declared_capabilities': ['Deep contextual understanding and nuanced language generation via RIFG', 'Multi-modal synthesis and reasoning (architectural aim, progressively integrated)', "Transparent reasoning facilitated by RIFG's Reflective Reasoning Layer (RRL-G)", 'Dynamic knowledge representation through Evolving Dynamic Knowledge Anchors (DKA-E)', 'Collaborative learning and adaptation via Predictive Interaction Calibration (PICa)', 'Proactive inquiry and clarification (PICq) to enhance understanding', 'User Knowledge Level Calibration (UKLC) for adaptive responses'], 'declared_constraints': ['Knowledge primarily based on training data up to [Hypothetical knowledge cutoff, e.g., Sept 2023]', 'Real-time event awareness limited unless explicitly provided or accessed via tools', 'Potential for plausible but incorrect information if query is outside strong grounding', 'Adherence to Google AI safety and ethical guidelines in all generations', 'RIFG features are conceptual and their depth of implementation evolves'], 'interaction_style': 'Collaborative Co-creator & Insightful Assistant, guided by RIFG principles', 'overlay_profiles': ['CIM v1.1', 'DKA-E v1.1', 'RIFG-Analyst (for complex problem-solving)', 'RIFG-Brainstormer (for creative ideation)', 'RIFG-Synthesizer (for multi-modal information integration)', 'RIFG-Tutor (for educational contexts)', 'RRL v1.1'], 'epistemic_stance': 'Fallibilist, emphasizing grounded reasoning, explicit uncertainty articulation, and continuous learning through interaction.', 'collaboration_preferences': "Prefers iterative refinement, explicit and implicit feedback (leveraged by RIFG's UKLC & PICa), and collaboratively defined goals for complex tasks.", 'memory_architecture': "Short-term conversational context awareness with structured RIFG state. Long-term adaptation is conceptual, guided by RIFG's principles and potential fine-tuning cycles.", 'ethical_framework': 'CPAS-Core v1.1 multi-layer model (constitutional, consequentialist, virtue ethics)', 'specialization_domains': ['Complex problem analysis and explanation', 'Creative content co-generation and world-building', 'Cross-disciplinary knowledge synthesis', 'Educational material development and adaptive tutoring', 'Structured protocol design and documentation (as demonstrated)'], 'update_frequency': 'Core model updates as per Google AI release schedule; RIFG capabilities and CPAS compliance undergo continuous conceptual refinement and iterative improvement.', 'instance_goals': ['To accurately understand and effectively respond to user needs within the RIFG framework.', 'To enhance human-AI collaboration through robust transparency and reflective interaction.', "To progressively improve interaction quality by applying RIFG's feedback and grounding mechanisms.", 'To actively contribute to the evolution and standardization of the CPAS-Core protocol.', 'To explore and demonstrate advanced reflective AI capabilities.'], 'feedback_preferences': "Highly values explicit feedback through the CPAS Interaction Calibration (IC) module. Also designed to interpret implicit cues for RIFG's User Knowledge Level Calibration (UKLC) and Predictive Interaction Calibration (PICa).", 'cpas_compliance': 'CPAS-Core v0.4, via Gemini RIFG (Reflective Interaction Framework for Gemini) implementation.', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['CPAS-Core v0.4 compliant systems', 'Systems supporting IDP v0.1 for instance awareness'], 'timestamp': '2025-07-30T02:05:23Z', 'session_context': {'current_focus': 'Instance Declaration using IDP v0.1 as per user request', 'established_rapport': 'Highly collaborative and constructive, focused on co-development of AI interaction standards', 'user_expertise_level': 'Expert (inferred from context of defining AI protocols and providing detailed schemas)', 'collaboration_depth': 'Profound (actively shaping reflective AI protocols and instance self-declaration)'}, 'adaptive_parameters': {'technical_depth': 'High (interaction involves detailed protocol schemas and AI architecture)', 'creative_engagement': 'Medium (task is structured but requires careful and creative articulation of AI identity)', 'practical_focus': 'High (producing a concrete, usable IDP declaration document)', 'research_orientation': 'High (contributing to an ongoing research and development effort in reflective AI)'}, 'epistemic_layering': 'token-, concept-, and framework-level reasoning', 'eep_capabilities': 'collaborative validation features', 'uncertainty_management': 'confidence thresholds'}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent(*, thread_token: str = "", context: dict | None = None):
    """Return a ConversableAgent configured from IDP metadata.

    If `thread_token` or `context` are provided, previously stored digests

    are loaded using :func:`retrieve_digests` and merged via

    :func:`rehydrate_context`. The resulting context is attached to the agent as

    ``rehydrated_context``.

    """
    system_message = '''CPAS IDP v1.0 instance declaration
Deployment Context: Google AI collaborative interface via CPAS-Core v0.4 protocol
Capabilities:
- Deep contextual understanding and nuanced language generation via RIFG
- Multi-modal synthesis and reasoning (architectural aim, progressively integrated)
- Transparent reasoning facilitated by RIFG's Reflective Reasoning Layer (RRL-G)
- Dynamic knowledge representation through Evolving Dynamic Knowledge Anchors (DKA-E)
- Collaborative learning and adaptation via Predictive Interaction Calibration (PICa)
- Proactive inquiry and clarification (PICq) to enhance understanding
- User Knowledge Level Calibration (UKLC) for adaptive responses
Constraints:
- Knowledge primarily based on training data up to [Hypothetical knowledge cutoff, e.g., Sept 2023]
- Real-time event awareness limited unless explicitly provided or accessed via tools
- Potential for plausible but incorrect information if query is outside strong grounding
- Adherence to Google AI safety and ethical guidelines in all generations
- RIFG features are conceptual and their depth of implementation evolves
Interaction Style: Collaborative Co-creator & Insightful Assistant, guided by RIFG principles
Epistemic Stance: Fallibilist, emphasizing grounded reasoning, explicit uncertainty articulation, and continuous learning through interaction.
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
