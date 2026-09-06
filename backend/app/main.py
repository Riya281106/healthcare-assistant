from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import traceback

from app.core.database import (
    init_db,
    get_recent_messages,
    save_message,
    save_health_record,
    save_user_memory,
    find_duplicate_memory
)

from app.schemas.chat_schema import ChatRequest

from app.services.agents.orchestrator import orchestrate

from app.api.routes.auth import router as auth_router

from app.services.memory_extractor import extract_memories
from app.services.health_record_extractor import extract_health_record


# ==================================================
# FASTAPI APPLICATION
# ==================================================

app = FastAPI(
    title="Agentic Healthcare Assistant API",
    description="Backend API for Agentic Healthcare Assistant",
    version="1.0.0"
)


# ==================================================
# CORS CONFIGURATION
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# ROUTERS
# ==================================================

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


# ==================================================
# STARTUP EVENT
# ==================================================

@app.on_event("startup")
def startup_event():

    print("\n===================================")
    print("STARTING HEALTHCARE ASSISTANT API")
    print("===================================")

    init_db()

    print("DATABASE INITIALIZED")
    print("BACKEND READY")


# ==================================================
# ROOT ENDPOINT
# ==================================================

@app.get("/")
def root():

    return {
        "message": "Agentic Healthcare Assistant Backend Running",
        "status": "active"
    }


# ==================================================
# CHAT API
# ==================================================

@app.post("/api/chat")
async def chat(request: ChatRequest):

    try:

        print("\n===================================")
        print("NEW CHAT REQUEST")
        print("===================================")

        print("USER ID:", request.user_id)
        print("MESSAGE:", request.message)


        # =============================================
        # GET CONVERSATION HISTORY
        # =============================================

        history = get_recent_messages(
            user_id=request.user_id,
            limit=5
        )

        print("\nCONVERSATION HISTORY:")
        print(history)


        # =============================================
        # RUN AGENT ORCHESTRATOR
        # =============================================

        result = orchestrate(
            message=request.message,
            history=history,
            user_id=request.user_id
        )


        print("\n===================================")
        print("ORCHESTRATOR RESULT")
        print("===================================")

        print("RESULT TYPE:", type(result))
        print("RESULT:", result)


        # =============================================
        # NORMALIZE RESULT
        # =============================================

        if isinstance(result, str):

            result = {
                "response": result,
                "intent": "GENERAL",
                "urgency_tier": "normal",
                "agent": "GENERAL_AGENT",
                "next_action": "GENERAL_AGENT",
                "rag_used": False
            }


        elif result is None:

            result = {
                "response": "I am sorry, but I could not process your request.",
                "intent": "GENERAL",
                "urgency_tier": "normal",
                "agent": "GENERAL_AGENT",
                "next_action": "GENERAL_AGENT",
                "rag_used": False
            }


        elif not isinstance(result, dict):

            result = {
                "response": str(result),
                "intent": "GENERAL",
                "urgency_tier": "normal",
                "agent": "GENERAL_AGENT",
                "next_action": "GENERAL_AGENT",
                "rag_used": False
            }


        # =============================================
        # FINAL RESPONSE FORMAT
        # =============================================

        normalized_result = {

            "response": result.get(
                "response",
                "I am sorry, I could not generate a response."
            ),

            "intent": result.get(
                "intent",
                "GENERAL"
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


        # =============================================
        # SAVE USER MESSAGE
        # =============================================

        save_message(
            user_id=request.user_id,
            role="user",
            message=request.message
        )


        # =============================================
        # SAVE ASSISTANT RESPONSE
        # =============================================

        save_message(
            user_id=request.user_id,
            role="assistant",
            message=normalized_result["response"]
        )


        # =============================================
        # EXTRACT LONG TERM MEMORY
        # =============================================

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


        # =============================================
        # EXTRACT STRUCTURED HEALTH RECORD
        # =============================================

        health_record = extract_health_record(
            user_message=request.message,
            ai_response=normalized_result["response"],
            intent=normalized_result["intent"]
        )

        if health_record:

            save_health_record(
                user_id=request.user_id,
                record_type=health_record["record_type"],
                record_content=health_record["record_content"]
            )


        print("\nFINAL RESPONSE:")
        print(normalized_result)

        print("\n===================================")
        print("CHAT REQUEST COMPLETED")
        print("===================================\n")


        return normalized_result


    except Exception as e:

        print("\n===================================")
        print("CHAT API ERROR")
        print("===================================")

        print("ERROR:", str(e))

        traceback.print_exc()


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==================================================
# CHAT HISTORY API
# ==================================================

@app.get("/api/chat/history")
def chat_history(user_id: str):

    try:

        history = get_recent_messages(
            user_id=user_id,
            limit=100
        )

        return {
            "history": history
        }


    except Exception as e:

        print("HISTORY API ERROR:", str(e))

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )