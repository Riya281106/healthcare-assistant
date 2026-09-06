from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str = "GENERAL"
    urgency_tier: str = "normal"
    agent: str = "GENERAL_LLM"
    next_action: str = "GENERAL_LLM"
    rag_used: bool = False


class HistoryResponse(BaseModel):
    history: List[Dict[str, Any]]