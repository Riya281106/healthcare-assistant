from pydantic import BaseModel
from typing import Optional


class ProfileResponse(BaseModel):
    id: int
    name: Optional[str] = None
    email: str
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    blood_group: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    created_at: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    blood_group: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None