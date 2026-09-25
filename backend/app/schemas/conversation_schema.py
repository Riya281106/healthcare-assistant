from pydantic import BaseModel
from typing import List, Optional


class MessageItem(BaseModel):
    role: str
    message: str
    created_at: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    history: List[MessageItem]


class ClearHistoryResponse(BaseModel):
    deleted_count: int