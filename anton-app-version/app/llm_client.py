import litellm
from app.config import settings
import os
import logging

logger = logging.getLogger(__name__)

# Set API keys for litellm so it can route to any provider
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.gemini_api_key:
    os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

async def generate_response(prompt: str, thread_id: str = None, model: str = None) -> str:
    """
    Generate response using litellm.
    `thread_id` can be used to manage conversation history or proxy to a backend thread system.
    """
    chosen_model = model or settings.active_model
    
    # In a full implementation, you would store and retrieve previous messages using the thread_id
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": prompt}
    ]
    
    logger.debug(f"Calling LLM ({chosen_model}) for thread {thread_id} with {len(messages)} messages.")
    
    response = await litellm.acompletion(
        model=chosen_model,
        messages=messages,
    )
    
    logger.debug(f"LLM successfully returned response for thread {thread_id}.")
    return response.choices[0].message.content
