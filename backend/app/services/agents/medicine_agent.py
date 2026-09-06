from app.services.llm.service import get_ai_response
from app.services.rag.retriever import retrieve_medical_context


def run_medicine_agent(
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
You are the Medicine Agent inside an Agentic Healthcare Platform.

MEDICAL KNOWLEDGE:
{medical_context}

USER QUESTION:
{message}

Rules:

- Use the retrieved information as supporting knowledge.
- Do not diagnose.
- Do not prescribe medication.
- Do not provide personalized dosage instructions.
- Do not recommend changing prescribed medication.
- Explain information clearly and cautiously.
- Recommend consulting a healthcare professional when appropriate.
- Do not mention internal systems.
"""

    else:

        grounded_message = f"""
You are the Medicine Agent inside an Agentic Healthcare Platform.

USER QUESTION:
{message}

Rules:

- Provide cautious general medicine information.
- Do not diagnose.
- Do not prescribe.
- Do not provide personalized dosage instructions.
- Recommend professional advice when appropriate.
"""


    response = get_ai_response(
        message=grounded_message,
        history=history,
        memories=memories
    )


    return {

        "message": str(response),

        "urgency_tier": "normal",

        "agent": "MEDICINE_AGENT",

        "rag_used": bool(medical_context)
    }