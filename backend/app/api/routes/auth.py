from fastapi import APIRouter, HTTPException, Request, status

from app.core.database import create_user, get_user_by_email
from app.core.rate_limit import RateLimiter
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse, UserPublic

router = APIRouter()

# Brute-force protection (per server process).
#   login: 8 tries per 5 minutes for one email from one address, 40 per 5 minutes per address
#   register: 10 new accounts per hour per address
login_limiter = RateLimiter(max_calls=8, window_seconds=300)
login_ip_limiter = RateLimiter(max_calls=40, window_seconds=300)
register_limiter = RateLimiter(max_calls=10, window_seconds=3600)

# A real bcrypt hash of a random string. Checked when the email is unknown so that
# "no such account" and "wrong password" take the same time (no account probing).
_DUMMY_HASH = hash_password("not-a-real-password-just-for-timing")


def reset_limiters() -> None:
    login_limiter.reset()
    login_ip_limiter.reset()
    register_limiter.reset()


def _client_ip(http: Request) -> str:
    return http.client.host if http.client else "unknown"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, http: Request):
    if not register_limiter.allow(_client_ip(http)):
        raise HTTPException(status_code=429, detail="Too many sign-ups from this device. Please try again later.")

    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    password_hash = hash_password(payload.password)
    user = create_user(payload.name, payload.email, password_hash)

    token = create_access_token({"sub": str(user["id"])})

    return TokenResponse(
        access_token=token,
        user=UserPublic(id=user["id"], name=user["name"], email=user["email"]),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, http: Request):
    email = payload.email.lower()
    ip = _client_ip(http)

    if not login_ip_limiter.allow(ip) or not login_limiter.allow(f"{ip}|{email}"):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please wait a few minutes and try again.",
        )

    user = get_user_by_email(email)

    if not user:
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token({"sub": str(user["id"])})

    return TokenResponse(
        access_token=token,
        user=UserPublic(id=user["id"], name=user["name"], email=user["email"]),
    )
