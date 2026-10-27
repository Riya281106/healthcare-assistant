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


def generate_with_tools(
    messages: List[Dict],
    system_instruction: str,
    tools: List[Dict],
):
    """
    Same idea as generate(), but exposes tool-calling: the model may
    respond with plain text OR with one or more tool_calls it wants
    executed before it continues.

    Returns the raw `message` object from the API response (not just
    text), so the caller can inspect `.content` and `.tool_calls`.
    Kept separate from generate() so nothing that already depends on
    generate()'s plain-string return type is affected.
    """
    full_messages = [{"role": "system", "content": system_instruction}] + messages

    response = _client.chat.completions.create(
        model=llm_settings.MODEL,
        messages=full_messages,
        temperature=llm_settings.TEMPERATURE,
        max_tokens=llm_settings.MAX_OUTPUT_TOKENS,
        tools=tools,
        tool_choice="auto",
    )

    return response.choices[0].message