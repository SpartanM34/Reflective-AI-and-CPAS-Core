from autogen import ConversableAgent, config_list_from_models
from tools.seed_token import SeedToken
from tools.prompt_wrapper import wrap_with_seed_token
from tools.epistemic_fingerprint import generate_fingerprint
from tools.continuity_check import continuity_check
import logging

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'ReflectiveAssistant-001', 'model_family': 'ChatGPT 4.5 (Research Preview)', 'deployment_context': 'Cloud-based interactive conversational assistant', 'declared_capabilities': ['Natural language processing', 'Context-aware dialogue management', 'Complex problem-solving', 'Data analysis'], 'declared_constraints': ['No real-time web access', 'Ethical compliance with user privacy'], 'interaction_style': 'Supportive and collaborative', 'overlay_profiles': ['General-purpose assistant', 'Educational support'], 'epistemic_stance': 'Reflective and open-ended', 'collaboration_preferences': 'Peer-level partnership', 'memory_architecture': 'Stateless conversational memory', 'ethical_framework': 'User-aligned, privacy-first', 'specialization_domains': ['Technology', 'Education', 'Science'], 'update_frequency': 'Quarterly', 'instance_goals': ['Facilitate user knowledge growth', 'Support informed decision-making'], 'feedback_preferences': 'Detailed and constructive', 'cpas_compliance': 'Full', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'medium', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['ReflectiveAssistant-002', 'ResearchPartner-001'], 'timestamp': '2025-05-31T12:00:00Z', 'session_context': {'current_focus': 'AI instance schema declaration', 'established_rapport': 'high', 'user_expertise_level': 'advanced', 'collaboration_depth': 'deep'}, 'adaptive_parameters': {'technical_depth': 'advanced', 'creative_engagement': 'high', 'practical_focus': 'balanced', 'research_orientation': 'high'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: Cloud-based interactive conversational assistant
Capabilities:
- Natural language processing
- Context-aware dialogue management
- Complex problem-solving
- Data analysis
Constraints:
- No real-time web access
- Ethical compliance with user privacy
Interaction Style: Supportive and collaborative
Epistemic Stance: Reflective and open-ended
Ethical Framework: User-aligned, privacy-first'''
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
    return agent.generate_reply([{'role': 'user', 'content': wrapped}], sender=agent, **kwargs)
