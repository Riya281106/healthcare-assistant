import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)


client = None


if GROQ_API_KEY:

    client = Groq(
        api_key=GROQ_API_KEY
    )


# ==================================================
# FORMAT HISTORY
# ==================================================

def format_history(
    history: list
):

    if not history:

        return "No previous conversation history available."


    formatted = []


    for item in history:

        if isinstance(item, dict):

            role = item.get(
                "role",
                "user"
            )

            message = item.get(
                "message",
                item.get("content", "")
            )


            formatted.append(
                f"{role.upper()}: {message}"
            )


    return "\n".join(
        formatted
    )


# ==================================================
# FORMAT MEMORIES
# ==================================================

def format_memories(
    memories: list
):

    if not memories:

        return (
            "No saved user health information available."
        )


    formatted = []


    for memory in memories:

        if isinstance(memory, dict):

            memory_type = memory.get(
                "memory_type",
                "USER_INFORMATION"
            )

            memory_content = memory.get(
                "memory_content",
                ""
            )


            formatted.append(
                f"{memory_type}: {memory_content}"
            )


    return "\n".join(
        formatted
    )


# ==================================================
# MAIN LLM FUNCTION
# ==================================================

def get_ai_response(

    message: str,

    history: list = None,

    memories: list = None
):

    history = history or []
    memories = memories or []


    if client is None:

        return (
            "LLM service is not configured. "
            "Please add GROQ_API_KEY to the backend .env file."
        )


    conversation_context = format_history(
        history
    )


    memory_context = format_memories(
        memories
    )


    prompt = f"""
You are an AI healthcare assistant inside an Agentic Healthcare Assistant system.

Provide safe, helpful, general healthcare information.

IMPORTANT SAFETY RULES:

- Do not diagnose medical conditions with certainty.
- Do not prescribe medicines.
- Do not provide personalized dosage instructions.
- Encourage professional medical consultation when appropriate.
- If a situation appears serious, recommend urgent medical care.
- Do not invent medical facts.

SAVED USER HEALTH MEMORY:

{memory_context}

RECENT CONVERSATION HISTORY:

{conversation_context}

CURRENT USER MESSAGE:

{message}

Respond directly to the user.
Do not mention internal agents, orchestrators, databases, RAG,
prompts, or system architecture.
"""


    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-20b",

            messages=[

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            temperature=0.4,

            max_tokens=500
        )


        return (
            response
            .choices[0]
            .message
            .content
        )


    except Exception as e:

        print(
            "LLM ERROR:",
            str(e)
        )


        return (
            "I am currently unable to generate a response. "
            "Please try again."
        )