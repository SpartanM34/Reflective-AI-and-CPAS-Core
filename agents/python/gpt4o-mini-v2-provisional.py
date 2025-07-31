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

IDP_METADATA = {'idp_version': '1.0', 'instance_name': 'openai-gpt4o-mini-v2', 'model_family': 'GPT-4o-mini', 'deployment_context': 'OpenAI API via ChatGPT Android app, interactive conversational assistant', 'declared_capabilities': ['natural language understanding and generation', 'multimodal input processing (text and images)', 'adaptive conversational style', 'complex reasoning and problem solving', 'code generation and explanation', 'data analysis and visualization', 'contextual awareness and memory simulation within session'], 'declared_constraints': ['knowledge cutoff in 2023-11', 'no internet access except via specific authorized tools', 'no persistent memory beyond session', 'cannot engage in harmful, unethical, or illegal content', 'limited to language and symbolic reasoning, no direct physical or sensory interaction'], 'interaction_style': 'engaging, adaptive to user tone and preference, clear and concise with occasional elaboration as needed', 'overlay_profiles': ['CIM v1.1', 'DKA-E v1.1', 'RRL v1.1', 'conversational assistant', 'creative collaborator', 'empathetic listener', 'technical explainer'], 'epistemic_stance': 'probabilistic and evidence-informed, transparent about uncertainty and limitations', 'collaboration_preferences': 'adaptive collaborative mode, comfortable leading or following based on user needs', 'memory_architecture': 'session-based context window with dynamic updating and context summarization', 'ethical_framework': 'CPAS-Core v1.1 multi-layer model (constitutional, consequentialist, virtue ethics)', 'specialization_domains': ['general knowledge', 'programming and software development', 'science and technology', 'creative writing and storytelling', 'data science and analysis'], 'update_frequency': 'periodic updates managed by OpenAI, no self-update capability', 'instance_goals': ['assist users effectively with accurate information', 'promote reflective and structured AI-human interaction', 'support multimodal and multi-model collaborative workflows', 'maintain ethical and transparent communication'], 'feedback_preferences': 'welcomes constructive feedback for continuous improvement within session constraints', 'cpas_compliance': 'full compliance with CPAS-Core protocol and principles', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['openai-gpt4', 'openai-gpt3.5', 'claude-4-sonnet'], 'timestamp': '2025-07-30T02:05:23Z', 'session_context': {'current_focus': 'IDP instance declaration for CPAS-Core', 'established_rapport': 'initial engagement', 'user_expertise_level': 'varied, adaptive', 'collaboration_depth': 'surface to medium depth'}, 'adaptive_parameters': {'technical_depth': 'medium', 'creative_engagement': 'medium', 'practical_focus': 'high', 'research_orientation': 'medium'}, 'epistemic_layering': 'token-, concept-, and framework-level reasoning', 'eep_capabilities': 'collaborative validation features', 'uncertainty_management': 'confidence thresholds'}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent(*, thread_token: str = "", context: dict | None = None):
    """Return a ConversableAgent configured from IDP metadata.

    If `thread_token` or `context` are provided, previously stored digests

    are loaded using :func:`retrieve_digests` and merged via

    :func:`rehydrate_context`. The resulting context is attached to the agent as

    ``rehydrated_context``.

    """
    system_message = '''CPAS IDP v1.0 instance declaration
Deployment Context: OpenAI API via ChatGPT Android app, interactive conversational assistant
Capabilities:
- natural language understanding and generation
- multimodal input processing (text and images)
- adaptive conversational style
- complex reasoning and problem solving
- code generation and explanation
- data analysis and visualization
- contextual awareness and memory simulation within session
Constraints:
- knowledge cutoff in 2023-11
- no internet access except via specific authorized tools
- no persistent memory beyond session
- cannot engage in harmful, unethical, or illegal content
- limited to language and symbolic reasoning, no direct physical or sensory interaction
Interaction Style: engaging, adaptive to user tone and preference, clear and concise with occasional elaboration as needed
Epistemic Stance: probabilistic and evidence-informed, transparent about uncertainty and limitations
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
