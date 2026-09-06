import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "Agentic AI Healthcare Assistant"
    APP_VERSION: str = "0.1.0"

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

settings = Settings()

if not settings.SECRET_KEY:
    raise ValueError(
        "SECRET_KEY is missing. Please add it to your .env file."
    )