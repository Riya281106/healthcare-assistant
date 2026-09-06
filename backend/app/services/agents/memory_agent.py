from app.core.database import get_user_memories


def run_memory_agent(user_id: str):

    if not user_id:

        return {
            "response": "I need a valid user ID to retrieve your saved health information.",
            "urgency_tier": "normal",
            "agent": "MEMORY_AGENT",
            "rag_used": False
        }

    memories = get_user_memories(
        user_id=user_id,
        limit=100
    )

    if not memories:

        return {
            "response": (
                "I currently do not have any saved health information "
                "about you."
            ),
            "urgency_tier": "normal",
            "agent": "MEMORY_AGENT",
            "rag_used": False
        }

    allergies = []
    conditions = []
    medications = []
    other_memories = []

    for memory in memories:

        if not isinstance(memory, dict):
            continue

        memory_type = memory.get(
            "memory_type",
            ""
        ).upper()

        memory_content = memory.get(
            "memory_content",
            ""
        )

        if not memory_content:
            continue

        if memory_type == "ALLERGY":

            allergies.append(memory_content)

        elif memory_type == "CONDITION":

            conditions.append(memory_content)

        elif memory_type == "MEDICATION":

            medications.append(memory_content)

        else:

            other_memories.append(memory_content)

    sections = []

    if allergies:

        sections.append(
            "Allergies:\n" +
            "\n".join(f"- {item}" for item in allergies)
        )

    if conditions:

        sections.append(
            "Medical Conditions:\n" +
            "\n".join(f"- {item}" for item in conditions)
        )

    if medications:

        sections.append(
            "Medications:\n" +
            "\n".join(f"- {item}" for item in medications)
        )

    if other_memories:

        sections.append(
            "Other Health Information:\n" +
            "\n".join(f"- {item}" for item in other_memories)
        )

    response = "Here is the health information I remember about you:\n\n"

    response += "\n\n".join(sections)

    return {
        "response": response,
        "urgency_tier": "normal",
        "agent": "MEMORY_AGENT",
        "rag_used": False
    }