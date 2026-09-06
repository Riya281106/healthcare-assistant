import os
from dotenv import load_dotenv

load_dotenv()


class LLMSettings:
    PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    MAX_OUTPUT_TOKENS: int = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "800"))
    API_KEY: str = os.getenv("GROQ_API_KEY")


llm_settings = LLMSettings()

if not llm_settings.API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing. Please add it to your .env file."
    )