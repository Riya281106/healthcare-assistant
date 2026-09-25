from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.database import get_recent_messages, delete_user_messages
from app.schemas.conversation_schema import (
    ConversationHistoryResponse,
    ClearHistoryResponse
)


router = APIRouter(prefix="/api/conversations", tags=["Conversation History"])


@router.get("/history", response_model=ConversationHistoryResponse)
def read_my_history(
    limit: int = Query(default=50, ge=1, le=500),
    current_user=Depends(get_current_user)
):

    user_id = str(current_user["id"])

    history = get_recent_messages(user_id=user_id, limit=limit)

    return {"history": history}


@router.delete("/history", response_model=ClearHistoryResponse)
def clear_my_history(current_user=Depends(get_current_user)):

    user_id = str(current_user["id"])

    deleted_count = delete_user_messages(user_id)

    return {"deleted_count": deleted_count}