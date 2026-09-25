from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import get_user_profile, update_user_profile
from app.schemas.profile_schema import ProfileResponse, ProfileUpdateRequest


router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
def read_my_profile(current_user=Depends(get_current_user)):

    profile = get_user_profile(current_user["id"])

    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user=Depends(get_current_user)
):

    fields = payload.dict(exclude_unset=True)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    updated = update_user_profile(current_user["id"], fields)

    if not updated:
        raise HTTPException(status_code=400, detail="Profile update failed")

    return get_user_profile(current_user["id"])