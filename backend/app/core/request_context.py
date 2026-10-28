"""
Per-request context (request id + user id).

Stored in ContextVars so every log line written while handling a request can
carry the same request_id without passing it through every function.
FastAPI runs sync endpoints in a worker thread and copies the context into it,
so values set in middleware are visible inside endpoints and the code they call.
"""

from contextvars import ContextVar
from typing import Optional

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_user_id: ContextVar[str] = ContextVar("user_id", default="-")


def set_request_id(value: str):
    return _request_id.set(value)


def reset_request_id(token) -> None:
    _request_id.reset(token)


def get_request_id() -> str:
    return _request_id.get()


def set_user_id(value: Optional[str]) -> None:
    _user_id.set(str(value) if value is not None else "-")


def get_user_id() -> str:
    return _user_id.get()
