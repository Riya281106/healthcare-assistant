from app.services.llm.service import get_ai_response
from app.services.rag.retriever import retrieve_medical_context


def run_report_agent(
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


    grounded_message = f"""
You are the Report Analysis Agent of an Agentic Healthcare Platform.

RETRIEVED MEDICAL KNOWLEDGE:
{medical_context if medical_context else "No relevant medical context found."}

USER QUESTION:
{message}

Instructions:

- Explain medical terminology in simple language.
- Do not diagnose the user.
- Do not invent test values or report results.
- Do not prescribe treatment.
- Clearly communicate uncertainty.
- Recommend consulting a qualified healthcare professional
  for personal report interpretation.
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

        "rag_used": bool(medical_context)
    }