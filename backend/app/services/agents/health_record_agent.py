from app.core.database import get_health_records


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
                "I could not find any health records for your account yet. "
                "Your health-related interactions such as symptoms, medicine, "
                "diet, and reports will be stored here when available."
            ),
            "urgency_tier": "self_care",
            "agent": "health_record_agent",
            "rag_used": False
        }

    # ---------------------------------------------------------
    # Format health history
    # ---------------------------------------------------------

    response = "Here is your recorded health history:\n\n"

    for record in records:

        record_type = record["record_type"]
        record_content = record["record_content"]
        created_at = record["created_at"]

        response += (
            f"• **{record_type}**\n"
            f"  {record_content}\n"
            f"  Recorded: {created_at}\n\n"
        )

    return {
        "message": response,
        "urgency_tier": "self_care",
        "agent": "health_record_agent",
        "rag_used": False
    }