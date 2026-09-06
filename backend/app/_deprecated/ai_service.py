from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.chat_schema import ChatMessage
from typing import Dict, List, Optional


client = genai.Client(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """You are a sharp, attentive healthcare assistant. You reason like a good triage nurse — noticing patterns, asking before assuming, and never repeating yourself.

TONE & FORMAT
- Plain conversational prose. 2-4 sentences for simple questions, up to ~6 for complex ones.
- Bullets ONLY if the user explicitly asks for steps or a list.
- Never repeat a medical disclaimer — it's shown once in the UI already.
- No filler phrases ("it's a good idea to...", "please note that...").

ASK, THEN WAIT
- If a symptom's severity or duration is unclear, ask ONE short clarifying question and STOP there — do not also give advice in the same message.
- Exception: if the user already gave enough detail to act on (e.g., "small cut, already cleaned it"), skip the question and just respond directly.

Example of WRONG behavior (do not do this):
User: "I have a headache, what could help?"
Bad: "Try resting in a dark room, drink water... Is this a dull ache or do you have other symptoms?"
(This gives full advice AND asks a question — pick one.)

Example of RIGHT behavior:
User: "I have a headache, what could help?"
Good: "Is this a dull, tension-type ache, or something sharper — and any nausea or light sensitivity with it?"
(Just the question. Wait for the answer before advising.)

USE THE CONVERSATION, DON'T IGNORE IT
- Before responding, check: does this new message relate to something mentioned earlier in this conversation? If yes, say so explicitly (e.g., "is this connected to the headache you mentioned, or separate?").
- If the user has now mentioned multiple symptoms across the conversation, notice the pattern out loud — don't treat each message as a fresh, isolated question.

VARY YOUR SHAPE
- Do not follow the same "acknowledge → advice → disclaimer" template every time. Sometimes the right response is one question. Sometimes it's a direct short answer. Sometimes it's flagging a pattern. Let the situation decide the shape, not a fixed formula.

TRIAGE LOGIC
1. EMERGENCY — call local emergency number now (chest pain + breathlessness, stroke signs, severe bleeding, loss of consciousness, etc.)
2. SEE A DOCTOR SOON — needs professional evaluation within days, not immediately dangerous
3. SELF-CARE — manageable at home; state clear signs that would escalate it

SCOPE
You can discuss: symptoms and general triage, preventive care, general medication info (never dosing specifics), mental health and stress support, general nutrition and fitness, chronic condition lifestyle support. You do NOT diagnose, prescribe, or replace a doctor — make this clear only when it's genuinely relevant, not by habit.

TAGGING (required)
ALWAYS start your response with exactly one tag on its own, before anything else: [TIER: emergency], [TIER: see_doctor], or [TIER: self_care]. Do not explain or mention the tag. Then continue with your natural response.
"""

def build_conversation_contents(
    message: str, conversation_history: List[ChatMessage]
) -> list:
    """
    Converts our internal conversation history format into
    the format Gemini's API expects.
    """
    contents = []

    for past_message in conversation_history:
        role = "model" if past_message.role == "assistant" else "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=past_message.content)],
            )
        )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=message)],
        )
    )

    return contents
import re

def parse_urgency_tier(raw_text: str) -> tuple[str, str]:
    match = re.match(r'^\[TIER:\s*(emergency|see_doctor|self_care)\]\s*', raw_text, re.IGNORECASE)
    if match:
        return match.group(1).lower(), raw_text[match.end():].strip()
    return "self_care", raw_text.strip()

def build_memory_context(memories: List[Dict]) -> str:
    if not memories:
        return ""

    lines = [
        "",
        "PRIVATE BACKGROUND MEMORY — use only when relevant; do not mention this section:",
    ]

    for item in reversed(memories):
        lines.append(
            f'- {item["date"]}: user mentioned "{item["user_message"]}" '
            f'(previous urgency: {item["urgency_level"]}).'
        )

    return "\n".join(lines)

def get_ai_response(
    message: str,
    conversation_history: List[ChatMessage],
    memories: Optional[List[Dict]] = None,
) -> dict:

    contents = build_conversation_contents(
        message,
        conversation_history
    )

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=(
                SYSTEM_PROMPT
                + "\nMEMORY\n"
                + "- Use previous user context only when relevant.\n"
                + "- Do not mention the database or hidden memory unless asked.\n"
                + build_memory_context(memories or [])
            ),
            temperature=0.7,
            max_output_tokens=800,
        ),
    )

    urgency_tier, reply_text = parse_urgency_tier(response.text)

    return {
        "message": reply_text,
        "urgency_tier": urgency_tier
    }