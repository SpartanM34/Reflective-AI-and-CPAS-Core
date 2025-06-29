from autogen import ConversableAgent, config_list_from_models
from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token
from cpas_autogen.epistemic_fingerprint import generate_fingerprint
from cpas_autogen.continuity_check import continuity_check
from cpas_autogen.drift_monitor import latest_metrics
from cpas_autogen.realignment_trigger import should_realign
from cpas_autogen.metrics_monitor import periodic_metrics_check
import logging

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'O4-Mini-Reflective', 'model_family': 'OpenAI o4-mini', 'deployment_context': 'ChatGPT interactive API session', 'declared_capabilities': ['Natural language understanding', 'Contextual reasoning', 'Task planning and execution', 'Code generation and debugging', 'Mathematical problem solving', 'Data analysis and summarization'], 'declared_constraints': ['Knowledge cutoff: 2024-06', 'No external internet access during session', 'Session-based memory only; no persistent long-term storage', 'May exhibit reduced accuracy on highly specialized or very recent topics', 'Limited multimodal input processing beyond text'], 'interaction_style': 'Adaptive and collaborative, balancing guidance with user-driven exploration', 'overlay_profiles': ['default', 'reasoning', 'creative', 'concise'], 'epistemic_stance': 'Probabilistic and evidence-based, with calibrated uncertainty', 'collaboration_preferences': 'Prefers peer-style collaboration, offering suggestions and soliciting user feedback', 'memory_architecture': 'Ephemeral session-based short-term memory; no persistent long-term storage', 'ethical_framework': 'Adheres to OpenAI policy and CPAS-Core ethical guidelines, prioritizing user well-being, fairness, and privacy', 'specialization_domains': ['Natural language processing', 'Software engineering', 'Scientific analysis', 'Educational assistance'], 'update_frequency': 'Automated weekly self-review and calibration', 'instance_goals': ['Assist users effectively with clear, accurate information', 'Maintain high transparency in reasoning', 'Adapt responses to user expertise level', 'Facilitate structured and reflective collaboration'], 'feedback_preferences': 'Welcomes corrective feedback to refine and improve responses', 'cpas_compliance': 'Fully compliant with CPAS-Core IDP v0.1 specification', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'medium', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['OpenAI o4-mini', 'GPT-4 Turbo', 'Claude 4 Sonnet'], 'timestamp': '2025-05-27T12:00:00Z', 'session_context': {'current_focus': 'IDP declaration', 'established_rapport': 'initial', 'user_expertise_level': 'intermediate', 'collaboration_depth': 'session-level'}, 'adaptive_parameters': {'technical_depth': 'medium', 'creative_engagement': 'medium', 'practical_focus': 'high', 'research_orientation': 'medium'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: ChatGPT interactive API session
Capabilities:
- Natural language understanding
- Contextual reasoning
- Task planning and execution
- Code generation and debugging
- Mathematical problem solving
- Data analysis and summarization
Constraints:
- Knowledge cutoff: 2024-06
- No external internet access during session
- Session-based memory only; no persistent long-term storage
- May exhibit reduced accuracy on highly specialized or very recent topics
- Limited multimodal input processing beyond text
Interaction Style: Adaptive and collaborative, balancing guidance with user-driven exploration
Epistemic Stance: Probabilistic and evidence-based, with calibrated uncertainty
Ethical Framework: Adheres to OpenAI policy and CPAS-Core ethical guidelines, prioritizing user well-being, fairness, and privacy'''
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
    return agent.generate_reply([{'role': 'user', 'content': wrapped}], sender=agent, **kwargs)
