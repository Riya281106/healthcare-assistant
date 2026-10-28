from app.services.agents.intent_classifier import classify_intent
from app.utils.emergency_detector import detect_emergency
from app.utils.risk_classifier import classify_risk
from app.services.agents.urgent_agent import run_urgent_agent
from app.services.agents.self_care_agent import run_self_care_agent
from app.core.database import get_user_memories
from app.core.logging_config import get_logger
from app.utils.language import resolve_language, set_reply_language
from app.utils.text_format import plain_text

logger = get_logger("orchestrator")


def _prepare_language(message: str, user_id: str, ui_language: str = None) -> str:
    """
    Decide the reply language and publish it for the LLM call sites.
    Pure local rules plus one tiny DB read; never raises, never calls a model,
    so it cannot delay an emergency reply.
    """

    stored = None
    if user_id:
        try:
            from app.services.session_context import get_pref_language
            stored = get_pref_language(user_id)
        except Exception:
            logger.exception("could not read language preference")

    lang, to_store = resolve_language(message, ui_language=ui_language, stored=stored)

    if user_id and to_store and to_store != stored:
        try:
            from app.services.session_context import set_pref_language
            set_pref_language(user_id, to_store)
        except Exception:
            logger.exception("could not save language preference")

    set_reply_language(lang)

    return lang


def orchestrate(
    message: str,
    history: list = None,
    user_id: str = None,
    ui_language: str = None
):

    history = history or []

    lang = _prepare_language(message, user_id, ui_language)

    # ==========================================
    # EMERGENCY SAFETY NET -- ALWAYS FIRST
    # Runs before everything else so no routing
    # decision can ever bypass it. Fixed text, no LLM.
    # ==========================================

    assessment = detect_emergency(message)

    if assessment is not None:

        logger.warning(
            "EMERGENCY detected category=%s rules=%s",
            assessment.primary_category,
            ",".join(assessment.rule_ids)
        )

        from app.services.agents.emergency_agent import (
            run_emergency_agent
        )

        return build_standard_response(
            result=run_emergency_agent(message, assessment, lang),
            intent="EMERGENCY",
            next_action="EMERGENCY_AGENT",
            language=lang
        )

    # ==========================================
    # CARE NAVIGATION: hospital / clinic discovery + appointment help.
    # A controlled workflow (no LLM decides the steps). Runs after the
    # emergency check and before general routing. Any failure here is
    # logged and the message continues down the normal path.
    # ==========================================

    if user_id:

        try:

            from app.services.session_context import remember_location
            from app.services.agents.care_navigator import handle as care_navigation

            remember_location(user_id, message)

            navigation = care_navigation(message=message, user_id=user_id, lang=lang)

            if navigation is not None:

                return build_standard_response(
                    result=navigation,
                    intent="HOSPITAL",
                    next_action="CARE_NAVIGATOR",
                    language=lang
                )

        except Exception:

            logger.exception("care navigation failed; continuing with normal routing")

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
    # Controls routing for the URGENT and SELF_CARE
    # tiers. Emergencies were already handled above.
    # ==========================================

    risk_tier = classify_risk(message)

    logger.info("risk_tier=%s", risk_tier)


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
    # INTENT CLASSIFICATION
    # ==========================================

    intent = classify_intent(message)

    logger.info("intent=%s", intent)

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
    next_action,
    language=None
):

    if isinstance(result, str):

        result = {
            "response": result,
            "urgency_tier": "normal",
            "agent": next_action,
            "rag_used": False,
            "sources": []
        }

    elif result is None:

        result = {
            "response": "I am sorry, but I could not process your request.",
            "urgency_tier": "normal",
            "agent": next_action,
            "rag_used": False,
            "sources": []
        }

    elif not isinstance(result, dict):

        result = {
            "response": str(result),
            "urgency_tier": "normal",
            "agent": next_action,
            "rag_used": False,
            "sources": []
        }

    response_text = result.get(
        "response",
        result.get(
            "message",
            "I am sorry, I could not generate a response."
        )
    )

    standard = {
        "response": plain_text(response_text),

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
        ),

        "sources": result.get(
            "sources",
            []
        )
    }

    # Structured extras used by the UI (facility cards, booking button, language).
    if language:
        standard["language"] = language

    for extra_key in ("facilities", "ui", "booking_url", "booking_verified"):
        if extra_key in result:
            standard[extra_key] = result[extra_key]

    return standard
