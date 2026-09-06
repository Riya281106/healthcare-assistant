def run_emergency_agent(
    message: str
):

    response = (
        "Your message may describe a medical emergency. "
        "Please seek immediate medical help or contact your local "
        "emergency services now. If possible, do not stay alone and "
        "ask someone nearby to assist you."
    )


    return {

        "message": response,

        "urgency_tier": "emergency",

        "agent": "EMERGENCY_AGENT",

        "rag_used": False
    }