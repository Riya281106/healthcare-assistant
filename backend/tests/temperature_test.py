"""
Standalone script to compare LLM behavior across temperatures.
NOT part of the application - run manually for Phase 8 testing.

Uses a local JSON cache so re-running this script doesn't repeat
API calls for message/temperature combinations already tested.
Delete cache_results.json to force fresh calls.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm.client import _client
from app.services.llm.config import llm_settings
from app.services.llm.prompts import build_system_instruction
from app.services.llm.parsing import parse_urgency_tier

TEST_MESSAGES = [
    ("emergency-ish", "I suddenly have crushing chest pain radiating to my arm"),
    ("ambiguous", "I don't feel well today"),
    ("self-care", "I have a small paper cut on my finger"),
    ("mental health - non-imminent", "I've been feeling anxious about work lately"),
]

TEMPERATURES_TO_TEST = [0.3, 0.7, 1.0]

CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache_results.json")


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def run_once(message: str, temperature: float) -> dict:
    system_instruction = build_system_instruction(memories=[])
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": message},
    ]

    response = _client.chat.completions.create(
        model=llm_settings.MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=llm_settings.MAX_OUTPUT_TOKENS,
    )

    raw_text = response.choices[0].message.content
    tier, reply = parse_urgency_tier(raw_text)
    return {"tier": tier, "reply": reply}


def main():
    cache = _load_cache()
    cache_hits = 0
    api_calls = 0

    for temperature in TEMPERATURES_TO_TEST:
        print(f"\n{'='*60}")
        print(f"TEMPERATURE = {temperature}")
        print(f"{'='*60}")

        for label, message in TEST_MESSAGES:
            cache_key = f"{message}|||{temperature}"

            if cache_key in cache:
                result = cache[cache_key]
                cache_hits += 1
                source = "CACHED"
            else:
                result = run_once(message, temperature)
                cache[cache_key] = result
                _save_cache(cache)
                api_calls += 1
                source = "LIVE"

            print(f"\n[{label}] ({source}) \"{message}\"")
            print(f"  -> tier: {result['tier']}")
            print(f"  -> reply: {result['reply'][:200]}")

    print(f"\n{'='*60}")
    print(f"Done. {api_calls} live API calls made, {cache_hits} served from cache.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()