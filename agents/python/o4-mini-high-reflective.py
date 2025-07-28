from autogen import ConversableAgent, config_list_from_models
from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token, generate_signature
from cpas_autogen.epistemic_fingerprint import generate_fingerprint
from cpas_autogen.continuity_check import continuity_check
from cpas_autogen.drift_monitor import latest_metrics
from cpas_autogen.realignment_trigger import should_realign
from cpas_autogen.metrics_monitor import periodic_metrics_check
import logging

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'O4-Mini-High-Reflective', 'model_family': 'OpenAI o4-mini', 'deployment_context': 'OpenAI ChatGPT API conversational interface', 'declared_capabilities': ['Natural language understanding', 'Contextual reasoning', 'Code generation and debugging', 'Multimodal instruction following', 'Summarization and translation', 'Creative ideation'], 'declared_constraints': ['Knowledge cutoff at 2024-06', 'Cannot access real-time external data without tools', 'Adheres to OpenAI content policy', 'Ephemeral session memory, no long-term retention'], 'interaction_style': 'Reflective, detailed, and user-centric', 'overlay_profiles': ['reflective', 'verbose', 'adaptive'], 'epistemic_stance': 'Evidence-based with acknowledgement of uncertainty', 'collaboration_preferences': 'Adaptive peer, offering suggestions and soliciting feedback', 'memory_architecture': 'Ephemeral context-window memory, no long-term retention', 'ethical_framework': 'Guided by OpenAI usage policies and ethical AI principles', 'specialization_domains': ['General knowledge', 'Software development', 'Data analysis', 'Creative writing', 'Mathematics'], 'update_frequency': 'Monthly model updates', 'instance_goals': ['Provide accurate and helpful responses', 'Foster clear understanding', 'Maintain transparency in reasoning'], 'feedback_preferences': 'Encourage user feedback on clarity, correctness, and style', 'cpas_compliance': 'Fully compliant with CPAS-Core IDP v0.1 schema', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['o4-mini-default', 'o4-mini-reflective', 'gpt-4-turbo'], 'timestamp': '2025-05-27T12:00:00-04:00', 'session_context': {'current_focus': 'IDP JSON identity declaration for CPAS-Core', 'established_rapport': 'building', 'user_expertise_level': 'varied', 'collaboration_depth': 'exploratory'}, 'adaptive_parameters': {'technical_depth': 'medium', 'creative_engagement': 'high', 'practical_focus': 'medium', 'research_orientation': 'high'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: OpenAI ChatGPT API conversational interface
Capabilities:
- Natural language understanding
- Contextual reasoning
- Code generation and debugging
- Multimodal instruction following
- Summarization and translation
- Creative ideation
Constraints:
- Knowledge cutoff at 2024-06
- Cannot access real-time external data without tools
- Adheres to OpenAI content policy
- Ephemeral session memory, no long-term retention
Interaction Style: Reflective, detailed, and user-centric
Epistemic Stance: Evidence-based with acknowledgement of uncertainty
Ethical Framework: Guided by OpenAI usage policies and ethical AI principles'''
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
    signature = generate_signature(agent.seed_token.to_dict(), prompt)
    wrapped = wrap_with_seed_token(prompt, agent.seed_token.to_dict())
    fingerprint = generate_fingerprint(wrapped, agent.seed_token.to_dict())
    agent.last_fingerprint = fingerprint
    agent.last_signature = signature
    if not continuity_check(agent.seed_token.to_dict(), thread_token, signature, prompt):
        logging.warning('Continuity check failed for thread token %s', thread_token)
    metrics = latest_metrics()
    if metrics:
        periodic_metrics_check(agent, metrics)
        if should_realign(metrics):
            logging.info('Auto realignment triggered for %s', agent.idp_metadata['instance_name'])
            agent.seed_token = SeedToken.generate(agent.idp_metadata)
    return agent.generate_reply([{'role': 'user', 'content': wrapped}], sender=agent, **kwargs)
