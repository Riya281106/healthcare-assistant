from app.services.agents.intent_classifier import classify_intent
from app.utils.emergency_detector import is_emergency
from app.utils.risk_classifier import classify_risk
from app.services.agents.urgent_agent import run_urgent_agent
from app.services.agents.self_care_agent import run_self_care_agent
from app.core.database import get_user_memories


def orchestrate(
    message: str,
    history: list = None,
    user_id: str = None
):

    print("\n===================================")
    print("ORCHESTRATOR STARTED")
    print("===================================")

    print("MESSAGE:", message)
    print("USER ID:", user_id)

    history = history or []

    # ==========================================
    # NORMALIZE CONVERSATION HISTORY
    # ==========================================

    clean_history = []

    for item in history:

        if isinstance(item, dict):

            clean_history.append({
                "role": item.get("role", "user"),
                "message": item.get(
                    "message",
                    item.get("content", "")
                )
            })

    # ==========================================
    # RISK CLASSIFICATION
    # This now actively controls routing for the
    # URGENT and SELF_CARE tiers. EMERGENCY still
    # goes through the existing is_emergency()
    # check right below, untouched, since that
    # logic already works.
    # ==========================================

    risk_tier = classify_risk(message)

    print("RISK CLASSIFIER RESULT:", risk_tier)


    if risk_tier == "URGENT":

        result = run_urgent_agent(
            message=message,
            history=clean_history,
            memories=[]
        )

        return build_standard_response(
            result=result,
            intent="URGENT",
            next_action="URGENT_AGENT"
        )


    if risk_tier == "SELF_CARE":

        result = run_self_care_agent(
            message=message,
            history=clean_history,
            memories=[]
        )

        return build_standard_response(
            result=result,
            intent="SELF_CARE",
            next_action="SELF_CARE_AGENT"
        )


    # ==========================================
    # EMERGENCY PRIORITY CHECK
    # ==========================================

    if is_emergency(message):

        from app.services.agents.emergency_agent import (
            run_emergency_agent
        )

        result = run_emergency_agent(message)

        return build_standard_response(
            result=result,
            intent="EMERGENCY",
            next_action="EMERGENCY_AGENT"
        )

    # ==========================================
    # INTENT CLASSIFICATION
    # ==========================================

    intent = classify_intent(message)

    print("CLASSIFIED INTENT:", intent)

    # ==========================================
    # RETRIEVE LONG-TERM MEMORY
    # ==========================================

    memories = []

    if user_id:

        memories = get_user_memories(
            user_id=user_id,
            limit=50
        )

    # ==========================================
    # MEMORY RECALL AGENT
    # ==========================================

    if intent == "MEMORY_RECALL":

        from app.services.agents.memory_agent import (
            run_memory_agent
        )

        result = run_memory_agent(
            user_id=user_id
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="MEMORY_AGENT"
        )
    # ==========================================
    # SYMPTOM -> SELF_CARE_AGENT
    # By this point, risk_classifier has already
    # ruled out EMERGENCY and URGENT. Any remaining
    # personal symptom is therefore self-care level,
    # so we reuse the same well-tuned agent instead
    # of the older, separate SYMPTOM_AGENT.
    # ==========================================

    if intent == "SYMPTOM":

        result = run_self_care_agent(
            message=message,
            history=clean_history,
            memories=memories
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="SELF_CARE_AGENT"
        )
    # ==========================================
    # MEDICINE AGENT
    # ==========================================

    if intent == "MEDICINE":

        from app.services.agents.medicine_agent import (
            run_medicine_agent
        )

        result = run_medicine_agent(
            message=message,
            history=clean_history,
            memories=memories
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="MEDICINE_AGENT"
        )

    # ==========================================
    # REPORT AGENT
    # ==========================================

    if intent == "REPORT":

        from app.services.agents.report_agent import (
            run_report_agent
        )

        result = run_report_agent(
            message=message,
            history=clean_history,
            memories=memories
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="REPORT_AGENT"
        )

    # ==========================================
    # DIET & FITNESS AGENT
    # ==========================================

    if intent == "DIET_FITNESS":

        from app.services.agents.diet_fitness_agent import (
            run_diet_fitness_agent
        )

        result = run_diet_fitness_agent(
            message=message,
            history=clean_history,
            memories=memories
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="DIET_FITNESS_AGENT"
        )

    # ==========================================
    # HEALTH RECORD AGENT
    # ==========================================

    if intent == "HEALTH_RECORD":

        from app.services.agents.health_record_agent import (
            run_health_record_agent
        )

        result = run_health_record_agent(
            user_id=user_id,
            message=message,
            history=clean_history,
            memories=memories
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="HEALTH_RECORD_AGENT"
        )

    # ==========================================
    # REMINDER AGENT
    # ==========================================

    if intent == "REMINDER":

        from app.services.agents.reminder_agent import (
            run_reminder_agent
        )

        result = run_reminder_agent(
            user_id=user_id,
            message=message,
            history=clean_history,
            memories=memories
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="REMINDER_AGENT"
        )

    # ==========================================
    # HOSPITAL AGENT
    # ==========================================

    if intent == "HOSPITAL":

        from app.services.agents.hospital_agent import (
            run_hospital_agent
        )

        result = run_hospital_agent(
            user_id=user_id,
            message=message,
            history=clean_history,
            memories=memories
        )

        return build_standard_response(
            result=result,
            intent=intent,
            next_action="HOSPITAL_AGENT"
        )

    # ==========================================
    # GENERAL AGENT
    # ==========================================

    from app.services.agents.general_agent import (
        run_general_agent
    )

    result = run_general_agent(
        message=message,
        history=clean_history,
        memories=memories
    )

    return build_standard_response(
        result=result,
        intent=intent,
        next_action="GENERAL_AGENT"
    )


# ==================================================
# STANDARD RESPONSE FORMAT
# ==================================================

def build_standard_response(
    result,
    intent,
    next_action
):

    if isinstance(result, str):

        result = {
            "response": result,
            "urgency_tier": "normal",
            "agent": next_action,
            "rag_used": False
        }

    elif result is None:

        result = {
            "response": "I am sorry, but I could not process your request.",
            "urgency_tier": "normal",
            "agent": next_action,
            "rag_used": False
        }

    elif not isinstance(result, dict):

        result = {
            "response": str(result),
            "urgency_tier": "normal",
            "agent": next_action,
            "rag_used": False
        }

    return {
        "response": result.get(
            "response",
            result.get(
                "message",
                "I am sorry, I could not generate a response."
            )
        ),

        "intent": intent,

        "urgency_tier": result.get(
            "urgency_tier",
            "normal"
        ),

        "agent": result.get(
            "agent",
            next_action
        ),

        "next_action": next_action,

        "rag_used": result.get(
            "rag_used",
            False
        )
    }