from app.services.llm.service import get_ai_response


def run_diet_fitness_agent(
    message: str,
    history: list = None,
    memories: list = None
):

    history = history or []
    memories = memories or []


    prompt = f"""
You are the Diet and Fitness Agent of an Agentic Healthcare Platform.

USER QUESTION:
{message}

Provide general information about:

- Healthy eating
- Nutrition
- Exercise
- Fitness
- Lifestyle

Rules:

- Do not diagnose medical conditions.
- Do not create unsafe or extreme diet plans.
- Avoid personalized treatment advice.
- Keep recommendations practical and general.
"""


    response = get_ai_response(
        message=prompt,
        history=history,
        memories=memories
    )


    return {

        "message": str(response),

        "urgency_tier": "self_care",

        "agent": "DIET_FITNESS_AGENT",

        "rag_used": False
    }