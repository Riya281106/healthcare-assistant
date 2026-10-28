from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any

from app.core.config import settings


class ChatRequest(BaseModel):
    # NOTE: there is deliberately no user_id field. The server takes the user
    # from the login token. Accepting user_id from the browser let anyone
    # read or write another person's health data by changing one number.
    message: str

    # Language chosen in the UI selector: "auto" (default), "en", "hi", "mr",
    # "hinglish" ... Unknown values are ignored (treated as "auto").
    language: Optional[str] = "auto"

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > settings.MAX_MESSAGE_CHARS:
            raise ValueError(
                f"Message is too long (maximum {settings.MAX_MESSAGE_CHARS} characters)"
            )
        return v


class RagSource(BaseModel):
    title: str
    category: str
    section: str
    relevance_score: Optional[float] = None


class ChatResponse(BaseModel):
    response: str
    intent: str = "GENERAL"
    urgency_tier: str = "normal"
    agent: str = "GENERAL_LLM"
    next_action: str = "GENERAL_LLM"
    rag_used: bool = False
    sources: List[RagSource] = []


class HistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
