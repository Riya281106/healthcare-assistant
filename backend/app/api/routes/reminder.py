from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import (
    save_reminder,
    get_user_reminders,
    find_duplicate_reminder,
    deactivate_reminder,
    get_due_reminders
)
from app.schemas.reminder_schema import (
    ReminderCreateRequest,
    ReminderListResponse,
    ReminderResponse,
    ReminderCancelResponse
)


router = APIRouter(prefix="/api/reminders", tags=["Reminders"])


@router.get("/due", response_model=ReminderListResponse)
def list_my_due_reminders(current_user=Depends(get_current_user)):

    user_id = str(current_user["id"])

    due_reminders = get_due_reminders(user_id)

    return {"reminders": due_reminders}


@router.get("", response_model=ReminderListResponse)
def list_my_reminders(current_user=Depends(get_current_user)):

    user_id = str(current_user["id"])

    reminders = get_user_reminders(user_id)

    return {"reminders": reminders}


@router.post("", response_model=ReminderResponse)
def create_my_reminder(
    payload: ReminderCreateRequest,
    current_user=Depends(get_current_user)
):

    user_id = str(current_user["id"])

    duplicate = find_duplicate_reminder(
        user_id=user_id,
        reminder_text=payload.reminder_text,
        reminder_time=payload.reminder_time,
        frequency=payload.frequency
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="An identical active reminder already exists."
        )

    reminder = save_reminder(
        user_id=user_id,
        reminder_text=payload.reminder_text,
        reminder_time=payload.reminder_time,
        frequency=payload.frequency
    )

    return reminder


@router.delete("/{reminder_id}", response_model=ReminderCancelResponse)
def cancel_my_reminder(
    reminder_id: int,
    current_user=Depends(get_current_user)
):

    user_id = str(current_user["id"])

    my_reminders = get_user_reminders(user_id)

    owned_ids = {reminder["id"] for reminder in my_reminders}

    if reminder_id not in owned_ids:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found."
        )

    deactivate_reminder(reminder_id)

    return {
        "message": "Reminder cancelled successfully.",
        "reminder_id": reminder_id
    }