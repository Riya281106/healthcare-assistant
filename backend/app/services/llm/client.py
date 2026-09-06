from openai import OpenAI
from typing import List, Dict

from app.services.llm.config import llm_settings

_client = OpenAI(
    api_key=llm_settings.API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


def generate(messages: List[Dict[str, str]], system_instruction: str) -> str:
    """
    Sends a request to the configured Groq model and returns the raw
    text response. Contains NO prompt content and NO parsing logic —
    only the mechanics of calling the provider.
    """
    full_messages = [{"role": "system", "content": system_instruction}] + messages

    response = _client.chat.completions.create(
        model=llm_settings.MODEL,
        messages=full_messages,
        temperature=llm_settings.TEMPERATURE,
        max_tokens=llm_settings.MAX_OUTPUT_TOKENS,
    )

    return response.choices[0].message.content