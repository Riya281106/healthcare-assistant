from app.services.llm.service import get_ai_response
from app.services.rag.retriever import retrieve_medical_context


def run_self_care_agent(
    message: str,
    history: list = None,
    memories: list = None
):

    history = history or []
    memories = memories or []


    medical_context = retrieve_medical_context(
        message,
        top_k=1
    )


    context_block = (
        f"MEDICAL KNOWLEDGE:\n{medical_context}\n\n"
        if medical_context
        else ""
    )


    grounded_message = f"""
You are the Self-Care Agent of an Agentic Healthcare Platform.

This situation has already been classified as SELF_CARE —
low risk, manageable at home, no urgent medical attention needed
at this time.

{context_block}USER MESSAGE:
{message}

Respond the way a caring, knowledgeable friend would — naturally,
in plain conversational sentences.

Rules:
- - Reply in the SAME language AND the SAME script/style the user
  used. If they wrote in Hinglish (Hindi words typed in English
  letters), reply in Hinglish the same way — do not switch to
  Devanagari script. Match how a real person actually texts.
- Keep it short: 3-5 sentences for a simple question. Only go
  longer if the situation genuinely needs more detail.
- Do NOT use tables, headers, or bullet-point lists unless the
  user specifically asks for a list.
- Do not diagnose with certainty. Do not prescribe medication.
- Briefly mention what would be a sign to see a doctor, worked
  naturally into the sentence — not as a separate labeled section.
- If the message has nothing to do with health, do not force a
  medical angle onto it — briefly redirect to health topics
  instead.
- If someone asks "do I have X disease," do not name a diagnosis
  as fact — explain that symptoms alone can't confirm it and a
  professional evaluation may be needed.
- Do not mention internal agents, tiers, or classifiers.
"""


    response = get_ai_response(
        message=grounded_message,
        history=history,
        memories=memories
    )


    return {

        "message": str(response),

        "urgency_tier": "self_care",

        "agent": "SELF_CARE_AGENT",

        "rag_used": bool(medical_context)
    }