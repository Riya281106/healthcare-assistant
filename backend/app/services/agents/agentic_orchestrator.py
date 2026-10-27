"""
AGENTIC ORCHESTRATOR
=====================

This replaces the if/elif intent routing in orchestrator.py with an
actual ReAct-style loop: the LLM sees the user's message plus a list
of tools, decides whether it needs to call one, looks at the result,
and either calls another tool or answers directly.

WHAT STAYS THE SAME AS THE ORIGINAL orchestrator.py (on purpose):
    - Emergency and Urgent detection remain hard-coded, deterministic
      checks that run BEFORE the LLM gets a turn. Safety-critical
      routing should never depend on whether a language model decided
      to call the right tool -- it must always fire.
    - The return shape (`build_standard_response`) is identical, so
      the /api/chat endpoint and frontend need zero changes to consume
      this new orchestrator as a drop-in replacement.

WHAT'S DIFFERENT:
    - Everything that isn't Emergency/Urgent now goes through a single
      tool-calling loop instead of ~10 separate if-branches. The model
      itself decides: "do I need the knowledge base? the user's
      records? should I set a reminder?" -- instead of a keyword list
      deciding for it.
"""

from app.utils.emergency_detector import is_emergency
from app.utils.risk_classifier import is_urgent
from app.services.agents.urgent_agent import run_urgent_agent
from app.services.agents.orchestrator import build_standard_response
from app.services.llm.client import generate_with_tools
from app.services.agents.tools import TOOL_SCHEMAS, run_tool
from app.services.agents.critique import critique_response

MAX_TOOL_STEPS = 4

SYSTEM_PROMPT = """You are an AI healthcare assistant inside an Agentic Healthcare Assistant system.

You have tools available for retrieving medical knowledge, the user's
own health records/memories, managing reminders, and finding hospitals.
Call a tool whenever it would make your answer more accurate or more
personalized than answering from general knowledge alone. Don't call a
tool you don't need.

SAFETY RULES (never break these):
- Do not diagnose medical conditions with certainty.
- Do not prescribe medicines or give personalized dosages.
- Encourage professional medical consultation when appropriate.
- If a situation appears serious, recommend urgent medical care.
- Do not invent medical facts -- if search_medical_knowledge returns
  nothing relevant, say so rather than making something up.
- Never mention internal tools, agents, orchestrators, or system
  architecture to the user. Respond as a single, coherent assistant.
"""


def agentic_orchestrate(message: str, history: list = None, user_id: str = None):

    history = history or []

    # ==========================================
    # HARD SAFETY NET -- unchanged from orchestrator.py
    # Runs before the LLM gets involved, on purpose.
    # ==========================================

    if is_emergency(message):
        from app.services.agents.emergency_agent import run_emergency_agent

        result = run_emergency_agent(message)
        return build_standard_response(result=result, intent="EMERGENCY", next_action="EMERGENCY_AGENT")

    if is_urgent(message):
        result = run_urgent_agent(message=message, history=history, memories=[])
        return build_standard_response(result=result, intent="URGENT", next_action="URGENT_AGENT")

    # ==========================================
    # AGENTIC LOOP
    # ==========================================

    clean_history = [
        {
            "role": "assistant" if item.get("role") == "assistant" else "user",
            "content": item.get("message", item.get("content", "")),
        }
        for item in history
        if isinstance(item, dict)
    ]

    messages = clean_history + [{"role": "user", "content": message}]

    tools_used = []
    all_sources = []
    retrieved_context_chunks = []

    for step in range(MAX_TOOL_STEPS):

        try:
            ai_message = generate_with_tools(
                messages=messages,
                system_instruction=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
            )
        except Exception as e:
            print("AGENTIC LOOP ERROR:", str(e))
            return build_standard_response(
                result={"response": "I'm having trouble processing that right now. Please try again."},
                intent="AGENTIC",
                next_action="AGENTIC_ORCHESTRATOR",
            )

        tool_calls = getattr(ai_message, "tool_calls", None)

        if not tool_calls:
            # Model is done reasoning -- this is the draft answer.
            # Run it through the groundedness check before returning it.
            draft_text = ai_message.content or "I'm sorry, I couldn't generate a response."

            final_text, was_revised, issues = critique_response(
                user_message=message,
                draft_response=draft_text,
                context_text="\n\n".join(retrieved_context_chunks),
            )

            return build_standard_response(
                result={
                    "response": final_text,
                    "rag_used": "search_medical_knowledge" in tools_used,
                    "sources": all_sources,
                },
                intent="AGENTIC",
                next_action=",".join(tools_used) if tools_used else "DIRECT_ANSWER",
            )

        # Model wants to call one or more tools. Record its tool-call
        # request in the conversation, execute each tool, and feed the
        # results back in as `role: tool` messages before looping again.
        messages.append({
            "role": "assistant",
            "content": ai_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tool_call in tool_calls:

            import json as _json

            tool_name = tool_call.function.name

            try:
                arguments = _json.loads(tool_call.function.arguments or "{}")
            except Exception:
                arguments = {}

            tools_used.append(tool_name)

            tool_result = run_tool(tool_name=tool_name, user_id=user_id, arguments=arguments)

            all_sources.extend(tool_result.get("sources", []))

            if tool_name == "search_medical_knowledge":
                retrieved_context_chunks.append(tool_result.get("text", ""))

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result.get("text", ""),
            })

    # Ran out of steps without a final answer -- fail safely rather
    # than looping forever.
    return build_standard_response(
        result={
            "response": "I gathered some information but wasn't able to finish putting together an answer. Could you rephrase your question?",
            "rag_used": "search_medical_knowledge" in tools_used,
            "sources": all_sources,
        },
        intent="AGENTIC",
        next_action="MAX_STEPS_REACHED",
    )
