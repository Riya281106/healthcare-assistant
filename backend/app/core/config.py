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

settings = Settings()

if not settings.SECRET_KEY:
    raise ValueError(
        "SECRET_KEY is missing. Please add it to your .env file."
    )
