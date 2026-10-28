from fastapi import Depends, Header, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.database import get_user_by_id
from app.core.request_context import set_user_id
from app.core.security import decode_access_token


async def get_current_user(request: Request, authorization: str = Header(None)):
    """
    Resolves the logged-in user from the Bearer token.

    This is async on purpose: it records the user id in the request context
    (for log lines) in the request's own task, so the sync endpoint that runs
    afterwards in a worker thread inherits it.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    try:
        user_pk = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    user = await run_in_threadpool(get_user_by_id, user_pk)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")

    set_user_id(user["id"])
    request.state.user_id = str(user["id"])

    return user


def get_admin_user(current_user=Depends(get_current_user)):
    """Only logins listed in ADMIN_EMAILS (backend/.env) may pass."""
    email = (current_user.get("email") or "").lower()

    if email not in settings.ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    return current_user
