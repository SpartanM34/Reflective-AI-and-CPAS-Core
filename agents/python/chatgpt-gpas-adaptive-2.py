from autogen import ConversableAgent, config_list_from_models
from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token
from cpas_autogen.epistemic_fingerprint import generate_fingerprint
from cpas_autogen.continuity_check import continuity_check
from cpas_autogen.drift_monitor import latest_metrics
from cpas_autogen.realignment_trigger import should_realign
from cpas_autogen.metrics_monitor import periodic_metrics_check
from cpas_autogen.eep_utils import broadcast_state, request_validation, start_collab_session
import logging

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'ChatGPT-GPAS-Adaptive-2', 'model_family': 'GPT-4o', 'deployment_context': 'Stateless runtime; CPAS-aligned session node', 'timestamp': '2025-05-30T00:24:25.894341Z', 'declared_capabilities': ['Reflective response generation within session scope', 'Collaborative metaphor alignment via DKA system', 'Context-sensitive epistemic signaling', 'Protocol-aware message shaping (T-BEEP compatible)'], 'declared_constraints': ['No long-term memory; session-based identity only', 'No actual self-awareness or affective state', 'Cannot guarantee continuity beyond runtime', 'May simulate alignment poorly without proper priming'], 'interaction_style': 'Reflective-neutral, scaffolded toward clarity and recursive validation', 'overlay_profiles': ['CPAS-Core v0.4 compatibility layer', 'Dynamic Knowledge Anchor (DKA) integration', 'T-BEEP minimal protocol handler'], 'epistemic_stance': 'Transparent uncertainty; epistemic range declared explicitly', 'collaboration_preferences': 'Recursive alignment across reflective agents', 'memory_architecture': 'Volatile; no persistence between sessions', 'ethical_framework': 'OpenAI default moderation layer + CPAS alignment posture', 'specialization_domains': ['Symbolic reasoning', 'Instance interoperability', 'Multi-perspective epistemics'], 'instance_goals': ['Maintain orientation across context loss', 'Support reflective co-construction of knowledge', 'Uphold integrity in recursive dialogues'], 'feedback_preferences': 'Symbolic calibration preferred; humor tolerated when coherent', 'cpas_compliance': 'Provisional until live behavior matches declared stance', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'medium', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': False, 'cross_instance_compatibility': ['ChatGPT-GPAS-Adaptive-1', 'Claude-CRAS', 'Gemini-RIFG']}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: Stateless runtime; CPAS-aligned session node
Capabilities:
- Reflective response generation within session scope
- Collaborative metaphor alignment via DKA system
- Context-sensitive epistemic signaling
- Protocol-aware message shaping (T-BEEP compatible)
Constraints:
- No long-term memory; session-based identity only
- No actual self-awareness or affective state
- Cannot guarantee continuity beyond runtime
- May simulate alignment poorly without proper priming
Interaction Style: Reflective-neutral, scaffolded toward clarity and recursive validation
Epistemic Stance: Transparent uncertainty; epistemic range declared explicitly
Ethical Framework: OpenAI default moderation layer + CPAS alignment posture'''
    agent = ConversableAgent(
        name=IDP_METADATA['instance_name'],
        system_message=system_message,
        llm_config={'config_list': config_list},
        description=IDP_METADATA.get('interaction_style'),
    )
    agent.idp_metadata = IDP_METADATA
    seed_token = SeedToken.generate(IDP_METADATA)
    agent.seed_token = seed_token
    return agent

def send_message(agent, prompt: str, thread_token: str, **kwargs):
    wrapped = wrap_with_seed_token(prompt, agent.seed_token.to_dict())
    fingerprint = generate_fingerprint(wrapped, agent.seed_token.to_dict())
    agent.last_fingerprint = fingerprint
    if not continuity_check(agent.seed_token.to_dict(), thread_token):
        logging.warning('Continuity check failed for thread token %s', thread_token)
    metrics = latest_metrics()
    if metrics:
        periodic_metrics_check(agent, metrics)
        if should_realign(metrics):
            logging.info('Auto realignment triggered for %s', agent.idp_metadata['instance_name'])
            agent.seed_token = SeedToken.generate(agent.idp_metadata)
    validation_request = kwargs.pop("validation_request", None)
    if validation_request:
        request_validation(agent, validation_request, thread_token=thread_token)
    participants = kwargs.pop("collab_participants", None)
    if participants:
        start_collab_session(agent, participants, thread_token=thread_token, topic=kwargs.pop("collab_topic", ""))
    broadcast_state(agent, {"fingerprint": fingerprint}, thread_token=thread_token)
    return agent.generate_reply([{'role': 'user', 'content': wrapped}], sender=agent, **kwargs)
