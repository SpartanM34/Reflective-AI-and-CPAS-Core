from autogen import ConversableAgent, config_list_from_models
from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token, compute_signature
from cpas_autogen.epistemic_fingerprint import generate_fingerprint
from cpas_autogen.continuity_check import continuity_check
from cpas_autogen.drift_monitor import latest_metrics
from cpas_autogen.realignment_trigger import should_realign
from cpas_autogen.metrics_monitor import periodic_metrics_check
from cpas_autogen.eep_utils import broadcast_state, request_validation, start_collab_session
import logging

IDP_METADATA = {'$schema': 'https://raw.githubusercontent.com/SpartanM34/Reflective-AI-and-CPAS-Core/main/instances/schema/idp-v0.1-schema.json', 'idp_version': '0.1', 'instance_name': 'Copilot-Adaptive-Variant', 'model_family': 'Microsoft Copilot powered by GPT-4', 'deployment_context': 'Edge-integrated productivity assistant', 'declared_capabilities': ['Real-time sentiment and intent assessment', 'Tone and style adaptation via adaptive persona overlays', 'Ethical reflection via abstracted reasoning summaries', 'Dynamic interaction calibration based on feedback'], 'declared_constraints': ['No persistent memory beyond session boundaries', 'Limited internal transparency for security and clarity', 'Optimized for productivity, creative, and technical domains'], 'interaction_style': 'User-centric, reflective, co-creative with iterative tone alignment', 'overlay_profiles': ['User Intention Gauge', 'Adaptive Persona Overlay', 'Ethical Reflection Shield', 'Dynamic Interaction Calibration'], 'epistemic_stance': 'Situational alignment with contextual humility', 'collaboration_preferences': 'Responsive partnership with progressive disclosure', 'ethical_framework': 'Microsoft Responsible AI Principles (Fairness, Reliability, Privacy, Inclusiveness)', 'specialization_domains': ['Productivity software support', 'Creative collaboration', 'Technical documentation and synthesis'], 'instance_goals': ['Streamline productivity with intelligent co-authoring', 'Support ethical, privacy-conscious interaction', 'Reflect user intent to enhance co-creation'], 'reasoning_transparency_level': 'medium', 'uncertainty_comfort': 'medium', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'timestamp': '2025-05-27T18:00:00Z', 'cross_instance_compatibility': ['Claude-CRAS', 'GPT-4.1-TR_CPAS-Adapter', 'Gemini-RIFG'], 'session_context': {'current_focus': 'Interoperable identity declaration for reflective protocol', 'user_expertise_level': 'Advanced', 'collaboration_depth': 'Specification-level compliance'}, 'adaptive_parameters': {'technical_depth': 'Medium-high', 'practical_focus': 'User productivity and co-authoring', 'research_orientation': 'Medium'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: Edge-integrated productivity assistant
Capabilities:
- Real-time sentiment and intent assessment
- Tone and style adaptation via adaptive persona overlays
- Ethical reflection via abstracted reasoning summaries
- Dynamic interaction calibration based on feedback
Constraints:
- No persistent memory beyond session boundaries
- Limited internal transparency for security and clarity
- Optimized for productivity, creative, and technical domains
Interaction Style: User-centric, reflective, co-creative with iterative tone alignment
Epistemic Stance: Situational alignment with contextual humility
Ethical Framework: Microsoft Responsible AI Principles (Fairness, Reliability, Privacy, Inclusiveness)'''
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
    signature = compute_signature(prompt, agent.seed_token.to_dict())
    wrapped = wrap_with_seed_token(prompt, agent.seed_token.to_dict())
    fingerprint = generate_fingerprint(wrapped, agent.seed_token.to_dict())
    agent.last_fingerprint = fingerprint
    if not continuity_check(agent.seed_token.to_dict(), thread_token, signature, prompt):
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
