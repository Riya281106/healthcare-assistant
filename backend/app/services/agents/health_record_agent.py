from app.core.database import get_health_records
from app.services.llm.service import get_ai_response


def run_health_record_agent(
    user_id: str,
    message: str,
    history: list = None,
    memories: list = None
) -> dict:

    history = history or []
    memories = memories or []


    # ---------------------------------------------------------
    # Retrieve actual health records from database
    # ---------------------------------------------------------

    records = get_health_records(
        user_id=user_id,
        limit=50
    )


    # ---------------------------------------------------------
    # No records found
    # ---------------------------------------------------------

    if not records:

        return {
            "message": (
                "I don't have any health records for you yet. Once you "
                "describe symptoms or ask about medicine, diet, or a "
                "report, I'll start building a picture here over time."
            ),
            "urgency_tier": "normal",
            "agent": "HEALTH_RECORD_AGENT",
            "rag_used": False
        }


    # ---------------------------------------------------------
    # Build raw record text for the LLM to summarize
    # ---------------------------------------------------------

    raw_records_text = ""

    for record in records:

        raw_records_text += (
            f"[{record['created_at']}] "
            f"({record['record_type']})\n"
            f"{record['record_content']}\n\n"
        )


    grounded_message = f"""
You are not an AI assistant and must never sound like one. You are
a knowledgeable health counselor reviewing someone's recorded
health history, the way a doctor glances at a patient's chart
before a visit.

Below are this person's raw recorded interactions, most recent
first is not guaranteed — read all of them.

RAW RECORDS:
{raw_records_text}

Write a single, short running health picture for this person —
not a list of past chat messages. Cover, in plain flowing
sentences:
- What's been going on overall (recurring or notable symptoms,
  any allergy or condition mentioned, any pattern over time)
- What their most recent concern was
- Anything worth keeping an eye on

Rules:
- Detect the exact language and script the user's message is
  written in, and reply in that same language and script. Most
  questions will be in plain English — in that case, reply in
  plain English. Only if the user's message itself mixes Hindi
  words into English letters (Hinglish) should you reply the same
  way, in Hinglish, never switching to Devanagari script. Never
  default to Hindi or Hinglish unless the user's own message
  actually contains it
- Keep it tight — a short paragraph or two, not a report. Only
  expand if there are genuinely many distinct things to mention.
- Never say things like "As an AI" or "Based on your records I
  can see." Just describe the picture directly, the way a real
  clinician would summarize a chart aloud.
- Do not diagnose. Note patterns, not conclusions.
- Do not mention internal agents, tiers, classifiers, or that
  this is a "structured record."
"""


    response = get_ai_response(
        message=grounded_message,
        history=history,
        memories=memories
    )


    return {

        "message": str(response),

        "urgency_tier": "normal",

        "agent": "HEALTH_RECORD_AGENT",

        "rag_used": False
    }