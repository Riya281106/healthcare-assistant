import time
import uuid

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_current_user
from app.api.routes.auth import router as auth_router
from app.api.routes.conversation import router as conversation_router
from app.api.routes.profile import router as profile_router
from app.api.routes.rag import router as rag_router
from app.api.routes.reminder import router as reminder_router
from app.api.routes.summary import router as summary_router
from app.core.database import (
    find_duplicate_memory,
    get_health_records,
    get_recent_messages,
    get_symptom_history,
    init_db,
    save_health_record,
    save_message,
    save_user_memory,
)
from app.core.logging_config import get_logger, setup_logging
from app.core.rate_limit import RateLimiter
from app.core.request_context import reset_request_id, set_request_id
from app.schemas.chat_schema import ChatRequest
from app.services.agents.emergency_agent import run_emergency_agent
from app.services.agents.orchestrator import build_standard_response, orchestrate
from app.services.conversation_summary_service import update_conversation_summary_if_needed
from app.services.health_record_extractor import extract_health_record
from app.services.memory_extractor import extract_memories
from app.utils.emergency_detector import detect_emergency

setup_logging()
logger = get_logger("api")

# 30 chat messages per minute per user. Messages that look like an emergency
# are never rate-limited.
chat_limiter = RateLimiter(max_calls=30, window_seconds=60)


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
    expose_headers=["X-Request-ID"],
)


# ==================================================
# REQUEST ID + ACCESS LOG
# Every log line for a request carries the same id, and the id is
# returned in the X-Request-ID response header so a user-reported
# error can be matched to the server log.
# ==================================================

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):

    request_id = uuid.uuid4().hex[:12]
    token = set_request_id(request_id)
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled error %s %s", request.method, request.url.path)
        reset_request_id(token)
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000
    user_id = getattr(request.state, "user_id", "-")

    logger.info(
        "%s %s -> %s in %.0fms (user=%s)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        user_id,
    )

    response.headers["X-Request-ID"] = request_id
    reset_request_id(token)
    return response


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

    logger.info("starting healthcare assistant API")

    init_db()

    logger.info("database initialized")

    try:

        from app.services.rag.knowledge_loader import load_knowledge_base

        rag_result = load_knowledge_base(force=False)

        logger.info(
            "RAG knowledge base ready: %s chunks indexed (%s file(s) re-embedded, %s unchanged)",
            rag_result["total_chunks"],
            rag_result["files_processed"],
            rag_result["files_skipped"],
        )

    except Exception as e:

        logger.warning("RAG knowledge base failed to load on startup: %s", e)

    logger.info("backend ready")


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
#
# Plain `def` (not `async def`): FastAPI runs it in a worker thread, so a
# slow LLM call no longer freezes the whole server for every other user.
# The user comes from the login token, never from the request body.
# ==================================================

def _normalize_result(result) -> dict:

    if not isinstance(result, dict):
        result = {
            "response": (
                result if isinstance(result, str)
                else "I am sorry, but I could not process your request."
            )
        }

    return {
        "response": result.get("response", "I am sorry, I could not generate a response."),
        "intent": result.get("intent", "GENERAL"),
        "urgency_tier": result.get("urgency_tier", "normal"),
        "agent": result.get("agent", "GENERAL_AGENT"),
        "next_action": result.get("next_action", "GENERAL_AGENT"),
        "rag_used": result.get("rag_used", False),
        "sources": result.get("sources", []),
    }


@app.post("/api/chat")
def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):

    user_id = str(current_user["id"])
    message = request.message
    started = time.perf_counter()

    looks_like_emergency = detect_emergency(message) is not None

    if not looks_like_emergency and not chat_limiter.allow(user_id):
        raise HTTPException(
            status_code=429,
            detail="You are sending messages too quickly. Please wait a moment and try again."
        )

    logger.info("chat request received (message_chars=%d)", len(message))

    # ---- conversation history (never let a DB hiccup block an emergency reply)
    try:
        history = get_recent_messages(user_id=user_id, limit=5)
    except Exception:
        logger.exception("could not load history; continuing without it")
        history = []

    # ---- run the agents
    try:

        result = orchestrate(message=message, history=history, user_id=user_id)

    except Exception:

        logger.exception("orchestrator failed")

        assessment = detect_emergency(message)

        if assessment is None:
            raise HTTPException(
                status_code=503,
                detail="The assistant is temporarily unavailable. Please try again in a moment."
            )

        # LLM/RAG is down but the message is an emergency: still give the safety reply.
        result = build_standard_response(
            result=run_emergency_agent(message, assessment),
            intent="EMERGENCY",
            next_action="EMERGENCY_AGENT"
        )

    normalized_result = _normalize_result(result)

    # ---- everything below is bookkeeping: failures are logged, never fatal,
    # because the person already has their answer.
    try:

        save_message(user_id=user_id, role="user", message=message)
        save_message(user_id=user_id, role="assistant", message=normalized_result["response"])

    except Exception:
        logger.exception("could not save chat messages")

    try:

        for memory in extract_memories(message):

            duplicate = find_duplicate_memory(
                user_id=user_id,
                memory_type=memory["memory_type"],
                memory_content=memory["memory_content"]
            )

            if not duplicate:
                save_user_memory(
                    user_id=user_id,
                    memory_type=memory["memory_type"],
                    memory_content=memory["memory_content"]
                )

    except Exception:
        logger.exception("could not save memories")

    try:

        health_record = extract_health_record(
            user_message=message,
            ai_response=normalized_result["response"],
            intent=normalized_result["intent"]
        )

        if health_record:
            save_health_record(
                user_id=user_id,
                record_type=health_record["record_type"],
                record_content=health_record["record_content"],
                symptom_name=health_record.get("symptom_name"),
                severity=health_record.get("severity"),
                duration_text=health_record.get("duration_text")
            )

    except Exception:
        logger.exception("could not save health record")

    background_tasks.add_task(
        update_conversation_summary_if_needed,
        user_id,
        normalized_result["intent"]
    )

    logger.info(
        "chat completed intent=%s tier=%s agent=%s rag=%s in %.0fms",
        normalized_result["intent"],
        normalized_result["urgency_tier"],
        normalized_result["agent"],
        normalized_result["rag_used"],
        (time.perf_counter() - started) * 1000,
    )

    return normalized_result


# ==================================================
# HEALTH RECORDS LIST API  (own records only)
# ==================================================

@app.get("/api/health-records")
def health_records_list(current_user=Depends(get_current_user)):

    try:

        records = get_health_records(user_id=str(current_user["id"]), limit=100)

        return {"records": records}

    except Exception:

        logger.exception("health records lookup failed")

        raise HTTPException(status_code=500, detail="Could not load health records.")


# ==================================================
# SYMPTOM HISTORY API  (own symptoms only)
# ==================================================

@app.get("/api/symptoms")
def symptom_history(current_user=Depends(get_current_user)):

    try:

        records = get_symptom_history(user_id=str(current_user["id"]), limit=200)

        return {"symptoms": records}

    except Exception:

        logger.exception("symptom history lookup failed")

        raise HTTPException(status_code=500, detail="Could not load symptom history.")


# NOTE: the old unauthenticated GET /api/chat/history?user_id=... was removed.
# Use the authenticated GET /api/conversations/history instead.
