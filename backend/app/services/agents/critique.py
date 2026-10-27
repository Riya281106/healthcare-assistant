"""
SELF-CRITIQUE / GROUNDEDNESS CHECK
====================================

A lightweight reflection step that runs after the agentic loop produces
a final answer. It re-reads the answer against whatever tool context
was actually retrieved (mainly search_medical_knowledge results) and
flags -- or lightly rewrites -- claims that aren't backed by anything
the tools actually returned.

This is a SEPARATE, cheap LLM call rather than folded into the main
loop's prompt, for two reasons:
1. A model grading its own answer inside the same context window tends
   to rubber-stamp itself. A fresh, narrowly-scoped prompt is a better
   check.
2. Keeping it separate means it can be disabled (CRITIQUE_ENABLED=false
   in .env) without touching the main agentic loop at all.
"""

import json
import os

from app.services.llm.client import generate

CRITIQUE_ENABLED = os.getenv("CRITIQUE_ENABLED", "true").lower() == "true"

CRITIQUE_SYSTEM_PROMPT = """You are a fact-checking reviewer for a healthcare assistant's draft reply.

You will be given:
- The user's question
- The draft reply the assistant is about to send
- The retrieved context (if any) that was available to ground the reply

Check whether specific medical claims in the draft reply (symptoms,
causes, treatments, medicine names, dosages, timeframes) are supported
by the retrieved context, well-established medical consensus, or are
reasonable safety guidance (e.g. "see a doctor").

Respond with ONLY a JSON object, no other text, no markdown fences:
{
  "grounded": true or false,
  "issues": ["short description of each unsupported or risky claim, if any"],
  "revised_response": "a corrected version of the reply, only if grounded is false and a safe correction is possible, otherwise empty string"
}

Do not flag general safety advice, disclaimers, or well-established
common knowledge (e.g. "drink water", "rest", "paracetamol is a common
pain reliever") just because it isn't in the retrieved context
verbatim. Only flag claims that are specific, could plausibly be wrong,
and are not backed by anything shown to you.
"""


def critique_response(user_message: str, draft_response: str, context_text: str = ""):
    """
    Returns (final_response, was_revised, issues_list).

    Fails open: if the critique call itself errors or returns something
    unparseable, the original draft_response is returned unchanged so a
    broken check never blocks a reply from reaching the user.
    """

    if not CRITIQUE_ENABLED or not draft_response:
        return draft_response, False, []

    prompt = f"""USER QUESTION:
{user_message}

DRAFT REPLY:
{draft_response}

RETRIEVED CONTEXT (may be empty):
{context_text or "(no context was retrieved for this reply)"}
"""

    try:
        raw = generate(
            messages=[{"role": "user", "content": prompt}],
            system_instruction=CRITIQUE_SYSTEM_PROMPT,
        )

        cleaned = (raw or "").strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        parsed = json.loads(cleaned)

        grounded = parsed.get("grounded", True)
        issues = parsed.get("issues", []) or []
        revised = (parsed.get("revised_response") or "").strip()

        if grounded:
            return draft_response, False, []

        if revised:
            print("CRITIQUE: response revised. Issues found:", issues)
            return revised, True, issues

        # Flagged as ungrounded but no safe rewrite offered. Fail open:
        # keep the original text (don't leave the user with nothing)
        # but log it so this is visible during testing.
        print("CRITIQUE: response flagged as potentially ungrounded:", issues)
        return draft_response, False, issues

    except Exception as e:
        print("CRITIQUE STEP FAILED (failing open, original reply kept):", str(e))
        return draft_response, False, []
