from app.services.llm.service import get_ai_response
from app.services.rag.retriever import retrieve_medical_context


def run_symptom_agent(
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


    if medical_context:

        grounded_message = f"""
You are the Symptom Assessment Agent of an Agentic Healthcare Platform.

Use the retrieved medical knowledge below as supporting information.

MEDICAL KNOWLEDGE:
{medical_context}

USER SYMPTOM:
{message}

Instructions:
- Provide cautious general health information.
- Do not diagnose with certainty.
- Do not prescribe medication.
- Explain possible general causes or considerations.
- Mention when professional medical evaluation may be appropriate.
- Do not mention internal agents or RAG systems.
"""

    else:

        grounded_message = f"""
You are the Symptom Assessment Agent of an Agentic Healthcare Platform.

USER SYMPTOM:
{message}

Provide cautious general health information.

Rules:
- Do not diagnose with certainty.
- Do not prescribe medication.
- Recommend professional medical care when appropriate.
"""


    response = get_ai_response(
        message=grounded_message,
        history=history,
        memories=memories
    )


    return {

        "message": str(response),

        "urgency_tier": "self_care",

        "agent": "SYMPTOM_AGENT",

        "rag_used": bool(medical_context)
    }