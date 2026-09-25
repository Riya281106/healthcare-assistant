from pydantic import BaseModel
from typing import Optional, List


class ReminderCreateRequest(BaseModel):
    reminder_text: str
    reminder_time: Optional[str] = None
    frequency: str = "once"


class ReminderResponse(BaseModel):
    id: int
    user_id: str
    reminder_text: str
    reminder_time: Optional[str] = None
    frequency: str
    status: str
    due_at: Optional[str] = None
    last_notified_at: Optional[str] = None
    created_at: Optional[str] = None

class ReminderListResponse(BaseModel):
    reminders: List[ReminderResponse]


class ReminderCancelResponse(BaseModel):
    message: str
    reminder_id: int