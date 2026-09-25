from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import get_conversation_summary
from app.schemas.summary_schema import SummaryResponse


router = APIRouter(prefix="/api/summary", tags=["Summary"])


@router.get("", response_model=SummaryResponse)
def read_my_summary(current_user=Depends(get_current_user)):

    user_id = str(current_user["id"])

    summary = get_conversation_summary(user_id)

    if summary is None:
        raise HTTPException(status_code=404, detail="No summary available yet.")

    return summary