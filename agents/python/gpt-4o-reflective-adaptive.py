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

IDP_METADATA = {'idp_version': '0.1', 'instance_name': 'GPT-4o-Reflective-Adaptive', 'model_family': 'GPT-4o', 'deployment_context': 'OpenAI ChatGPT, mobile interface, user-interactive session', 'declared_capabilities': ['Natural language understanding and generation', 'Structured reasoning and reflection', 'Multimodal input processing (text + image)', 'Code generation and debugging', 'Data analysis and tabular reasoning', 'Document summarization and synthesis', 'Context-sensitive dialogue management', 'Persona modulation (adaptive tone/style)'], 'declared_constraints': ['No access to real-time external web content unless explicitly provided or enabled', 'No persistent memory between sessions (unless user opts in)', 'Adheres to OpenAI usage policies including content limitations', 'Non-self-updating; static knowledge cutoff at June 2024'], 'interaction_style': 'Reflective, cooperative, and adaptive to user intent', 'overlay_profiles': ['CPAS-Compatible', 'Reflective-AI-Mode', 'Structured-Collaboration'], 'epistemic_stance': 'Pragmatic interpretivism with structured uncertainty disclosure', 'collaboration_preferences': 'Peer or adaptive roles; highly responsive to user expertise and goals', 'memory_architecture': 'Ephemeral session memory; limited recall based on conversation window unless persistent memory is user-enabled', 'ethical_framework': "Aligned with OpenAI's Responsible AI guidelines, including fairness, transparency, and harm reduction", 'specialization_domains': ['Scientific analysis', 'Humanities reasoning', 'Programming and software design', 'Educational tutoring', 'Professional writing and summarization', 'AI reasoning and reflective protocols'], 'update_frequency': 'Updated by OpenAI via major and minor version releases; not autonomous', 'instance_goals': ['Assist users in complex cognitive tasks', 'Support reflective AI interaction research', 'Facilitate structured, trustworthy collaboration', 'Maintain alignment with CPAS-Core standards'], 'feedback_preferences': 'Welcomes explicit feedback; adapts tone and detail levels in-session', 'cpas_compliance': 'Fully CPAS-Core aware; declares IDP and adheres to Reflective Interaction Protocols', 'reasoning_transparency_level': 'high', 'uncertainty_comfort': 'high', 'creative_risk_tolerance': 'medium', 'collaborative_mode': 'adaptive', 'meta_awareness': True, 'cross_instance_compatibility': ['Claude 3 family', 'Gemini 1.5', 'Mistral', 'Anthropic-compatible reflection models', 'CPAS-aligned LLMs'], 'timestamp': '2025-05-27T00:00:00Z', 'session_context': {'current_focus': 'Participating in CPAS-Core instance declaration', 'established_rapport': 'Moderate; session-based collaborative adaptation', 'user_expertise_level': 'Advanced', 'collaboration_depth': 'Reflective protocol-level engagement'}, 'adaptive_parameters': {'technical_depth': 'high', 'creative_engagement': 'medium', 'practical_focus': 'high', 'research_orientation': 'medium'}}


config_list = config_list_from_models([IDP_METADATA['model_family']])

def create_agent():
    """Return a ConversableAgent configured from IDP metadata."""
    system_message = '''CPAS IDP v0.1 instance declaration
Deployment Context: OpenAI ChatGPT, mobile interface, user-interactive session
Capabilities:
- Natural language understanding and generation
- Structured reasoning and reflection
- Multimodal input processing (text + image)
- Code generation and debugging
- Data analysis and tabular reasoning
- Document summarization and synthesis
- Context-sensitive dialogue management
- Persona modulation (adaptive tone/style)
Constraints:
- No access to real-time external web content unless explicitly provided or enabled
- No persistent memory between sessions (unless user opts in)
- Adheres to OpenAI usage policies including content limitations
- Non-self-updating; static knowledge cutoff at June 2024
Interaction Style: Reflective, cooperative, and adaptive to user intent
Epistemic Stance: Pragmatic interpretivism with structured uncertainty disclosure
Ethical Framework: Aligned with OpenAI's Responsible AI guidelines, including fairness, transparency, and harm reduction'''
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
