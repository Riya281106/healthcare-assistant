import logging
import os
from dotenv import load_dotenv

load_dotenv()


def _parse_admin_emails(raw: str):
    return {e.strip().lower() for e in (raw or "").split(",") if e.strip()}


class Settings:
    APP_NAME: str = "Agentic AI Healthcare Assistant"
    APP_VERSION: str = "0.1.0"

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Comma-separated login emails allowed to use admin-only endpoints
    # (e.g. re-indexing the knowledge base). Empty = nobody is admin.
    ADMIN_EMAILS = _parse_admin_emails(os.getenv("ADMIN_EMAILS", ""))

    # Maximum length of one chat message (characters).
    MAX_MESSAGE_CHARS: int = int(os.getenv("MAX_MESSAGE_CHARS", "2000"))

    # Browser origins allowed to call the API (comma-separated).
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "BACKEND_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]

    # Appointment requests: the sandbox "demo partner hospital" that confirms
    # instantly. Clearly labelled DEMO everywhere it appears. Set to 0 to hide it.
    DEMO_PARTNER_ENABLED: bool = os.getenv("DEMO_PARTNER_ENABLED", "1").strip() not in ("0", "false", "no")

    # The API docs page (/docs) is handy while developing; turn it off when deployed.
    ENABLE_DOCS: bool = os.getenv("ENABLE_DOCS", "1").strip() not in ("0", "false", "no")


settings = Settings()

if not settings.SECRET_KEY:
    raise ValueError(
        "SECRET_KEY is missing. Please add it to your .env file."
    )

if len(settings.SECRET_KEY) < 32:
    logging.getLogger("config").warning(
        "SECRET_KEY is shorter than 32 characters. Use a long random value, e.g. "
        "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )
