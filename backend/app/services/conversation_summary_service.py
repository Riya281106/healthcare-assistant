import json

from app.core.database import (
    get_recent_messages,
    upsert_conversation_summary
)

from app.services.llm.client import generate


# ==================================================
# RECORDABLE INTENTS
# Reuses the same list health_record_extractor.py
# already treats as "meaningful" health conversation,
# so the summary only updates when there's something
# worth summarizing.
# ==================================================

RECORDABLE_INTENTS = [
    "SYMPTOM",
    "URGENT",
    "SELF_CARE",
    "MEDICINE",
    "REPORT",
    "DIET_FITNESS"
]


# ==================================================
# SYSTEM INSTRUCTION FOR STRUCTURED SUMMARY
# ==================================================

SUMMARY_SYSTEM_INSTRUCTION = """
You are a structured healthcare conversation summarizer.

You will be given a user's recent conversation history with a
healthcare assistant. Produce a concise, structured overview of
what has been discussed.

STRICT SAFETY RULES:
- Do NOT diagnose any medical condition.
- Do NOT present anything as a confirmed medical fact.
- Use safe, neutral language such as "reported symptoms",
  "topics mentioned", "health-related observations", and
  "suggested follow-up" rather than clinical certainty.
- This is an AI-generated overview of conversations, not a
  medical report.

OUTPUT FORMAT:
Respond with ONLY valid JSON, no markdown, no code fences, no
extra text before or after it. Use exactly this shape:

{
  "main_concerns": ["..."],
  "symptoms": ["..."],
  "medicines": ["..."],
  "health_observations": ["..."],
  "urgency_level": "one short phrase, e.g. 'Routine' or 'Suggested follow-up soon'",
  "recommended_actions": ["..."],
  "overall_summary": "2-4 sentence plain-language overview"
}

If a field has nothing to report, return an empty list (or an
empty string for overall_summary/urgency_level) rather than
omitting the field.
"""


# ==================================================
# BUILD CONVERSATION TEXT BLOCK
# ==================================================

def _format_conversation_for_summary(history: list) -> str:

    lines = []

    for item in history:

        role = item.get("role", "user")
        message = item.get("message", "")

        lines.append(f"{role.upper()}: {message}")

    return "\n".join(lines)


# ==================================================
# PARSE LLM JSON RESPONSE SAFELY
# ==================================================

def _parse_summary_response(raw_text: str):

    if not raw_text:
        return None

    cleaned = raw_text.strip()

    # Defensive: strip accidental markdown code fences
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        parsed = json.loads(cleaned)
        return parsed

    except (json.JSONDecodeError, ValueError):
        print("SUMMARY PARSE ERROR — raw response was:")
        print(raw_text)
        return None


# ==================================================
# MAIN ENTRY POINT
# ==================================================

def update_conversation_summary_if_needed(user_id: str, intent: str):
    """
    Called after a chat turn. Only regenerates the summary when
    the current message's intent is meaningful health content,
    to avoid an LLM call on every single message.
    """

    if intent not in RECORDABLE_INTENTS:
        return None

    history = get_recent_messages(user_id=user_id, limit=20)

    if not history:
        return None

    conversation_text = _format_conversation_for_summary(history)

    try:
        raw_response = generate(
            messages=[
                {"role": "user", "content": conversation_text}
            ],
            system_instruction=SUMMARY_SYSTEM_INSTRUCTION
        )

    except Exception as e:
        print("SUMMARY GENERATION ERROR:", str(e))
        return None

    parsed = _parse_summary_response(raw_response)

    if not parsed:
        return None

    saved_summary = upsert_conversation_summary(
        user_id=user_id,
        overall_summary=parsed.get("overall_summary", ""),
        main_concerns=parsed.get("main_concerns", []),
        symptoms=parsed.get("symptoms", []),
        medicines=parsed.get("medicines", []),
        health_observations=parsed.get("health_observations", []),
        urgency_level=parsed.get("urgency_level", ""),
        recommended_actions=parsed.get("recommended_actions", [])
    )

    return saved_summary