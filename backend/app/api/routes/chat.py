from fastapi import APIRouter, HTTPException
import traceback

from app.schemas.chat_schema import ChatRequest

from app.services.agents.orchestrator import orchestrate

from app.core.database import (
    get_recent_messages,
    save_message,
    save_health_record,
    save_user_memory,
    find_duplicate_memory
)

from app.services.health_record_extractor import (
    extract_health_record
)

from app.services.memory_extractor import (
    extract_memories
)


router = APIRouter()


# ==================================================
# NORMALIZE RESULT
# ==================================================

def normalize_result(result):

    if result is None:

        return {

            "response": (
                "I am sorry, but I could not process your request."
            ),

            "intent": "OTHER",

            "urgency_tier": "normal",

            "agent": "GENERAL_AGENT",

            "next_action": "GENERAL_AGENT",

            "rag_used": False
        }


    if isinstance(result, str):

        return {

            "response": result,

            "intent": "OTHER",

            "urgency_tier": "normal",

            "agent": "GENERAL_AGENT",

            "next_action": "GENERAL_AGENT",

            "rag_used": False
        }


    return {

        "response": result.get(
            "response",
            "I am sorry, I could not generate a response."
        ),

        "intent": result.get(
            "intent",
            "OTHER"
        ),

        "urgency_tier": result.get(
            "urgency_tier",
            "normal"
        ),

        "agent": result.get(
            "agent",
            "GENERAL_AGENT"
        ),

        "next_action": result.get(
            "next_action",
            "GENERAL_AGENT"
        ),

        "rag_used": result.get(
            "rag_used",
            False
        )
    }


# ==================================================
# CHAT API
# ==================================================

@router.post("/chat")
async def chat(
    request: ChatRequest
):

    try:

        print("\n===================================")
        print("NEW CHAT REQUEST")
        print("===================================")

        print("USER ID:", request.user_id)
        print("MESSAGE:", request.message)


        # ==============================================
        # GET CONVERSATION HISTORY
        # ==============================================

        history = get_recent_messages(
            user_id=request.user_id,
            limit=10
        )


        # ==============================================
        # RUN AGENTIC ORCHESTRATOR
        # ==============================================

        result = orchestrate(

            message=request.message,

            history=history,

            user_id=request.user_id
        )


        # ==============================================
        # NORMALIZE RESPONSE
        # ==============================================

        final_result = normalize_result(
            result
        )


        # ==============================================
        # SAVE USER MESSAGE
        # ==============================================

        save_message(

            user_id=request.user_id,

            role="user",

            message=request.message
        )


        # ==============================================
        # SAVE AI RESPONSE
        # ==============================================

        save_message(

            user_id=request.user_id,

            role="assistant",

            message=final_result["response"]
        )


        # ==============================================
        # EXTRACT LONG TERM MEMORY
        # ==============================================

        extracted_memories = extract_memories(
            request.message
        )


        for memory in extracted_memories:

            duplicate = find_duplicate_memory(

                user_id=request.user_id,

                memory_type=memory["memory_type"],

                memory_content=memory["memory_content"]
            )


            if not duplicate:

                save_user_memory(

                    user_id=request.user_id,

                    memory_type=memory["memory_type"],

                    memory_content=memory["memory_content"]
                )


        # ==============================================
        # EXTRACT STRUCTURED HEALTH RECORD
        # ==============================================

        health_record = extract_health_record(

            user_message=request.message,

            ai_response=final_result["response"],

            intent=final_result["intent"]
        )


        if health_record:

            save_health_record(

                user_id=request.user_id,

                record_type=health_record["record_type"],

                record_content=health_record["record_content"]
            )


        print("\nFINAL RESULT:")
        print(final_result)

        print("===================================")
        print("CHAT COMPLETED")
        print("===================================\n")


        return final_result


    except Exception as e:

        print("\n===================================")
        print("CHAT API ERROR")
        print("===================================")

        print(str(e))

        traceback.print_exc()


        raise HTTPException(

            status_code=500,

            detail=str(e)
        )


# ==================================================
# CHAT HISTORY
# ==================================================

@router.get("/chat/history")
def chat_history(
    user_id: str
):

    try:

        history = get_recent_messages(

            user_id=user_id,

            limit=100
        )


        return {

            "history": history
        }


    except Exception as e:

        traceback.print_exc()

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )