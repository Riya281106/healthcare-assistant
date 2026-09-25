from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import traceback

from app.core.database import (
    init_db,
    get_recent_messages,
    save_message,
    save_health_record,
    save_user_memory,
    find_duplicate_memory,
    get_symptom_history
)

from app.schemas.chat_schema import ChatRequest

from app.services.agents.orchestrator import orchestrate

from app.api.routes.auth import router as auth_router
from app.api.routes.profile import router as profile_router
from app.api.routes.conversation import router as conversation_router
from app.api.routes.reminder import router as reminder_router
from app.api.routes.summary import router as summary_router
from app.api.routes.rag import router as rag_router

from app.services.memory_extractor import extract_memories
from app.services.health_record_extractor import extract_health_record
from app.services.conversation_summary_service import update_conversation_summary_if_needed
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
app.include_router(profile_router)
app.include_router(conversation_router)
app.include_router(reminder_router)
app.include_router(summary_router)
app.include_router(rag_router)

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

    try:

        from app.services.rag.knowledge_loader import load_knowledge_base

        rag_result = load_knowledge_base(force=False)

        print(
            f"RAG KNOWLEDGE BASE READY -- "
            f"{rag_result['total_chunks']} chunks indexed "
            f"({rag_result['files_processed']} file(s) (re)embedded, "
            f"{rag_result['files_skipped']} unchanged)"
        )

    except Exception as e:

        print(f"WARNING: RAG knowledge base failed to load on startup: {e}")

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
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):

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
                "rag_used": False,
                "sources": []
            }


        elif result is None:

            result = {
                "response": "I am sorry, but I could not process your request.",
                "intent": "GENERAL",
                "urgency_tier": "normal",
                "agent": "GENERAL_AGENT",
                "next_action": "GENERAL_AGENT",
                "rag_used": False,
                "sources": []
            }


        elif not isinstance(result, dict):

            result = {
                "response": str(result),
                "intent": "GENERAL",
                "urgency_tier": "normal",
                "agent": "GENERAL_AGENT",
                "next_action": "GENERAL_AGENT",
                "rag_used": False,
                "sources": []
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
            ),

            "sources": result.get(
                "sources",
                []
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
                record_content=health_record["record_content"],
                symptom_name=health_record.get("symptom_name"),
                severity=health_record.get("severity"),
                duration_text=health_record.get("duration_text")
            )

        # =============================================
        # UPDATE AUTO CONVERSATION SUMMARY (non-blocking)
        # =============================================

        background_tasks.add_task(
            update_conversation_summary_if_needed,
            request.user_id,
            normalized_result["intent"]
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
# HEALTH RECORDS LIST API
# ==================================================

@app.get("/api/health-records")
def health_records_list(user_id: str):

    try:

        from app.core.database import get_health_records

        records = get_health_records(
            user_id=user_id,
            limit=100
        )

        return {
            "records": records
        }


    except Exception as e:

        print("HEALTH RECORDS API ERROR:", str(e))

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==================================================
# SYMPTOM HISTORY API (Symptom Tracker / Health Journal)
# ==================================================

@app.get("/api/symptoms")
def symptom_history(user_id: str):

    try:

        records = get_symptom_history(
            user_id=user_id,
            limit=200
        )

        return {
            "symptoms": records
        }


    except Exception as e:

        print("SYMPTOM HISTORY API ERROR:", str(e))

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