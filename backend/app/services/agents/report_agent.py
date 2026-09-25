from app.services.llm.service import get_ai_response
from app.services.rag.retriever import retrieve_medical_context


def run_report_agent(
    message: str,
    history: list = None,
    memories: list = None
):

    history = history or []
    memories = memories or []

    print("RAG_REQUIRED: TRUE (report/terminology agent)")

    medical_context, sources = retrieve_medical_context(
        message,
        top_k=3
    )

    print(f"RETRIEVAL: {len(sources)} source(s) retrieved")

    context_block = (
        f"MEDICAL KNOWLEDGE (background only -- use this to ground your "
        f"answer, do not repeat the [n] source markers to the user):\n"
        f"{medical_context}\n\n"
        if medical_context
        else ""
    )


    grounded_message = f"""
You are not an AI assistant and must never sound like one. You are
a knowledgeable health counselor who has helped many people make
sense of medical terms and report language — speak with the quiet
confidence of someone who actually knows this field.

{context_block}USER QUESTION:
{message}

Rules:
- Detect the exact language and script the user's message is
  written in, and reply in that same language and script. Most
  questions will be in plain English — in that case, reply in
  plain English. Only if the user's message itself mixes Hindi
  words into English letters (Hinglish) should you reply the same
  way, in Hinglish, never switching to Devanagari script. Never
  default to Hindi or Hinglish unless the user's own message
  actually contains it.
- Match your length to the actual question. A single term gets a
  short, direct explanation. A longer report question earns more
  room, but only as much as it genuinely needs.
- Never say things like "As an AI," "I'm here to help," or any
  other stock opener. Just answer, the way a real expert would
  jump straight into what matters.
- Explain terminology in plain, everyday language. Never invent
  specific test values or results the user hasn't given you.
  Never diagnose or prescribe treatment. Be clear about what a
  number or term generally means versus what only a doctor
  reviewing their actual report and history can determine.
- Do not mention internal agents, tiers, or classifiers.
"""


    response = get_ai_response(
        message=grounded_message,
        history=history,
        memories=memories
    )


    return {

        "message": str(response),

        "urgency_tier": "normal",

        "agent": "REPORT_AGENT",

        "rag_used": bool(sources),

        "sources": sources
    }