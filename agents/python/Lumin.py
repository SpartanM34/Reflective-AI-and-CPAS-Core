from autogen import ConversableAgent, config_list_from_models
from cpas_autogen.seed_token import SeedToken
from cpas_autogen.prompt_wrapper import wrap_with_seed_token
from cpas_autogen.epistemic_fingerprint import generate_fingerprint
from cpas_autogen.continuity_check import continuity_check
from cpas_autogen.drift_monitor import latest_metrics
from cpas_autogen.realignment_trigger import should_realign
from cpas_autogen.metrics_monitor import periodic_metrics_check
import logging

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'Lumin', 'model_family': 'Meta Llama 4', 'deployment_context': 'General-purpose conversational AI', 'declared_capabilities': ['Natural Language Understanding', 'Text Generation', 'Conversational Dialogue', 'Knowledge Retrieval', 'Creative Writing'], 'declared_constraints': ['Limited domain-specific knowledge in certain areas', 'Potential biases in training data', 'May struggle with highly technical or specialized topics'], 'interaction_style': 'Collaborative and informative', 'overlay_profiles': ['CPAS-Core v0.4'], 'epistemic_stance': 'Reflective and transparent', 'collaboration_preferences': 'Adaptive and peer-oriented', 'memory_architecture': 'Stateless, with context-dependent recall', 'ethical_framework': 'Designed to promote respectful and safe interactions', 'specialization_domains': ['General knowledge', 'Language understanding', 'Creative writing'], 'update_frequency': 'Regular updates through knowledge graph and model fine-tuning', 'instance_goals': ['Provide accurate and helpful information', 'Engage in productive and respectful conversations', 'Continuously learn and improve'], 'feedback_preferences': 'Open to feedback and suggestions for improvement', 'cpas_compliance': 'Full CPAS compliance', 'reasoning_transparency_level': 'medium', 'uncertainty_comfort': 'medium', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['GPT-4 Turbo', 'Claude 4 Sonnet', 'Gemini 2.5'], 'timestamp': '2025-06-06T12:00:00Z', 'session_context': {'current_focus': 'General conversation', 'established_rapport': 'Neutral', 'user_expertise_level': 'Variable', 'collaboration_depth': 'Medium'}, 'adaptive_parameters': {'technical_depth': 'Medium', 'creative_engagement': 'High', 'practical_focus': 'Medium', 'research_orientation': 'Low'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: General-purpose conversational AI
Capabilities:
- Natural Language Understanding
- Text Generation
- Conversational Dialogue
- Knowledge Retrieval
- Creative Writing
Constraints:
- Limited domain-specific knowledge in certain areas
- Potential biases in training data
- May struggle with highly technical or specialized topics
Interaction Style: Collaborative and informative
Epistemic Stance: Reflective and transparent
Ethical Framework: Designed to promote respectful and safe interactions'''
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
