from fastapi import APIRouter, HTTPException, status

from app.core.database import create_user, get_user_by_email
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse, UserPublic

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    password_hash = hash_password(request.password)
    user = create_user(request.name, request.email, password_hash)

    token = create_access_token({"sub": str(user["id"])})

    return TokenResponse(
        access_token=token,
        user=UserPublic(id=user["id"], name=user["name"], email=user["email"]),
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = get_user_by_email(request.email.lower())

    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token({"sub": str(user["id"])})

    return TokenResponse(
        access_token=token,
        user=UserPublic(id=user["id"], name=user["name"], email=user["email"]),
    )