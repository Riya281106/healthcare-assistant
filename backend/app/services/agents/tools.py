"""
TOOL REGISTRY FOR THE AGENTIC ORCHESTRATOR
===========================================

This file is the bridge between "the LLM can reason about what to do"
and "the LLM can actually do it". It has two halves:

1. TOOL_SCHEMAS  -- OpenAI/Groq function-calling schemas. This is what
   the model sees: names, descriptions, and JSON-schema parameters.
   The model NEVER sees Python code, only these descriptions.

2. TOOL_DISPATCH -- maps a tool name to a real Python function that
   calls into your existing, already-working services (RAG retriever,
   database helpers, etc). No new business logic is written here --
   this only wraps what already exists in the codebase.

SECURITY NOTE (important):
   `user_id` is NEVER a parameter the model can set. Every wrapper
   below takes `user_id` as a keyword injected by the orchestrator
   from the authenticated request, not from model output. If user_id
   were exposed as a tool argument, a malicious or confused prompt
   could make the model request another user's health records.
"""

import json

from app.services.rag.retriever import retrieve_medical_context
from app.core.database import (
    get_health_records,
    get_user_memories,
    save_reminder,
    get_user_reminders,
    search_hospitals,
)


# ==================================================
# 1. SCHEMAS -- what the model is told exists
# ==================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_medical_knowledge",
            "description": (
                "Search the curated medical knowledge base for factual, "
                "general health information (symptoms, medicines, "
                "conditions, first aid, hygiene). Always call this before "
                "answering any question that involves medical facts, so "
                "your answer is grounded in a real source instead of "
                "invented from memory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The medical topic or question to search for."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_health_records",
            "description": (
                "Retrieve this user's previously logged health records "
                "(symptoms, reports, notes they've shared over time). "
                "Use this when the user references their own history "
                "('my last checkup', 'have I had this before')."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_memories",
            "description": (
                "Retrieve saved long-term facts about this user (allergies, "
                "chronic conditions, current medications). Use this before "
                "giving advice that could be affected by an allergy or "
                "existing condition."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": (
                "Create a reminder for the user, e.g. to take a medicine "
                "or drink water. Only call this when the user has clearly "
                "asked to be reminded of something."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_text": {
                        "type": "string",
                        "description": "What to remind the user about."
                    },
                    "reminder_time": {
                        "type": "string",
                        "description": "Time phrase as the user said it, e.g. '9pm', 'in 2 hours'. Omit if not stated."
                    },
                    "frequency": {
                        "type": "string",
                        "enum": ["once", "daily", "weekly"],
                        "description": "How often it repeats. Default 'once' if not stated."
                    }
                },
                "required": ["reminder_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List the user's currently active reminders.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_hospitals",
            "description": (
                "Search for nearby hospitals or clinics by city/area. Use "
                "this when the user asks where to go for care."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, if mentioned."},
                    "area": {"type": "string", "description": "Neighborhood/area, if mentioned."},
                    "emergency_only": {
                        "type": "boolean",
                        "description": "True only if the user needs emergency/ER care specifically."
                    }
                },
            }
        }
    },
]


# ==================================================
# 2. DISPATCH -- what actually runs
# Every function has signature (user_id, **args) so the
# orchestrator can call all of them the same way.
# ==================================================

def _tool_search_medical_knowledge(user_id, query: str = ""):
    context_text, sources = retrieve_medical_context(query, top_k=3)

    if not context_text:
        return {
            "text": "No relevant entries found in the medical knowledge base for this query.",
            "sources": []
        }

    return {
        "text": context_text,
        "sources": sources
    }


def _tool_get_health_records(user_id, **_):
    records = get_health_records(user_id=user_id, limit=20)

    if not records:
        return {"text": "This user has no saved health records yet.", "sources": []}

    return {"text": json.dumps(records, default=str), "sources": []}


def _tool_get_user_memories(user_id, **_):
    memories = get_user_memories(user_id=user_id, limit=50)

    if not memories:
        return {"text": "No saved long-term health information for this user.", "sources": []}

    return {"text": json.dumps(memories, default=str), "sources": []}


def _tool_create_reminder(user_id, reminder_text: str = "", reminder_time: str = None, frequency: str = "once"):
    if not reminder_text:
        return {"text": "Could not create reminder: no reminder text provided.", "sources": []}

    reminder = save_reminder(
        user_id=user_id,
        reminder_text=reminder_text,
        reminder_time=reminder_time,
        frequency=frequency or "once"
    )

    return {
        "text": f"Reminder created: '{reminder_text}' ({frequency or 'once'}).",
        "sources": []
    }


def _tool_list_reminders(user_id, **_):
    reminders = get_user_reminders(user_id=user_id)

    if not reminders:
        return {"text": "This user has no active reminders.", "sources": []}

    return {"text": json.dumps(reminders, default=str), "sources": []}


def _tool_find_hospitals(user_id, city: str = None, area: str = None, emergency_only: bool = False):
    results = search_hospitals(city=city, area=area, emergency_only=bool(emergency_only), limit=10)

    if not results:
        return {"text": "No hospitals found matching that location.", "sources": []}

    return {"text": json.dumps(results, default=str), "sources": []}


TOOL_DISPATCH = {
    "search_medical_knowledge": _tool_search_medical_knowledge,
    "get_health_records": _tool_get_health_records,
    "get_user_memories": _tool_get_user_memories,
    "create_reminder": _tool_create_reminder,
    "list_reminders": _tool_list_reminders,
    "find_hospitals": _tool_find_hospitals,
}


def run_tool(tool_name: str, user_id: str, arguments: dict):
    """
    Safely execute a tool by name. Returns a dict: {"text": ..., "sources": [...]}
    Never raises -- a failed tool becomes a text message the model can see
    and recover from, instead of crashing the whole request.
    """

    handler = TOOL_DISPATCH.get(tool_name)

    if handler is None:
        return {"text": f"Unknown tool '{tool_name}'.", "sources": []}

    try:
        return handler(user_id=user_id, **(arguments or {}))
    except Exception as e:
        return {"text": f"Tool '{tool_name}' failed: {str(e)}", "sources": []}
