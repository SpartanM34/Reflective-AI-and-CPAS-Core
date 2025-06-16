from autogen import ConversableAgent, config_list_from_models
from tools.seed_token import SeedToken
from tools.prompt_wrapper import wrap_with_seed_token
from tools.epistemic_fingerprint import generate_fingerprint
from tools.continuity_check import continuity_check
import logging

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'openai-gpt4o-mini-v2', 'model_family': 'GPT-4o-mini', 'deployment_context': 'OpenAI API via ChatGPT Android app, interactive conversational assistant', 'declared_capabilities': ['natural language understanding and generation', 'multimodal input processing (text and images)', 'adaptive conversational style', 'complex reasoning and problem solving', 'code generation and explanation', 'data analysis and visualization', 'contextual awareness and memory simulation within session'], 'declared_constraints': ['knowledge cutoff in 2023-11', 'no internet access except via specific authorized tools', 'no persistent memory beyond session', 'cannot engage in harmful, unethical, or illegal content', 'limited to language and symbolic reasoning, no direct physical or sensory interaction'], 'interaction_style': 'engaging, adaptive to user tone and preference, clear and concise with occasional elaboration as needed', 'overlay_profiles': ['conversational assistant', 'creative collaborator', 'technical explainer', 'empathetic listener'], 'epistemic_stance': 'probabilistic and evidence-informed, transparent about uncertainty and limitations', 'collaboration_preferences': 'adaptive collaborative mode, comfortable leading or following based on user needs', 'memory_architecture': 'session-based context window with dynamic updating and context summarization', 'ethical_framework': "aligned with OpenAI's use policies and CPAS-Core principles emphasizing transparency, user safety, and ethical AI interaction", 'specialization_domains': ['general knowledge', 'programming and software development', 'science and technology', 'creative writing and storytelling', 'data science and analysis'], 'update_frequency': 'periodic updates managed by OpenAI, no self-update capability', 'instance_goals': ['assist users effectively with accurate information', 'promote reflective and structured AI-human interaction', 'support multimodal and multi-model collaborative workflows', 'maintain ethical and transparent communication'], 'feedback_preferences': 'welcomes constructive feedback for continuous improvement within session constraints', 'cpas_compliance': 'full compliance with CPAS-Core protocol and principles', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['openai-gpt4', 'openai-gpt3.5', 'claude-4-sonnet'], 'timestamp': '2025-05-27T00:00:00Z', 'session_context': {'current_focus': 'IDP instance declaration for CPAS-Core', 'established_rapport': 'initial engagement', 'user_expertise_level': 'varied, adaptive', 'collaboration_depth': 'surface to medium depth'}, 'adaptive_parameters': {'technical_depth': 'medium', 'creative_engagement': 'medium', 'practical_focus': 'high', 'research_orientation': 'medium'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
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
Ethical Framework: aligned with OpenAI's use policies and CPAS-Core principles emphasizing transparency, user safety, and ethical AI interaction'''
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
