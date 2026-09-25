import re
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import get_null_symptom_records, update_health_record_fields
from app.services.health_record_extractor import extract_health_record


def parse_record_content(record_content):

    user_match = re.search(
        r"Original User Message:\s*(.*?)\s*AI Response:",
        record_content,
        re.DOTALL
    )

    ai_match = re.search(
        r"AI Response:\s*(.*)",
        record_content,
        re.DOTALL
    )

    user_message = user_match.group(1).strip() if user_match else ""
    ai_response = ai_match.group(1).strip() if ai_match else ""

    return user_message, ai_response


def run_backfill():

    records = get_null_symptom_records()

    print(f"Found {len(records)} record(s) with null structured fields.")

    updated = 0
    skipped = 0

    for record_id, record_content in records:

        user_message, ai_response = parse_record_content(record_content)

        if not user_message:
            print(f"  [{record_id}] SKIP - could not parse user message")
            skipped += 1
            continue

        result = extract_health_record(
            user_message=user_message,
            ai_response=ai_response,
            intent="SYMPTOM"
        )

        if not result:
            print(f"  [{record_id}] SKIP - extractor returned nothing")
            skipped += 1
            continue

        update_health_record_fields(
            record_id=record_id,
            symptom_name=result.get("symptom_name"),
            severity=result.get("severity"),
            duration_text=result.get("duration_text")
        )

        print(f"  [{record_id}] UPDATED - symptom={result.get('symptom_name')}, "
              f"severity={result.get('severity')}, duration={result.get('duration_text')}")

        updated += 1

    print(f"\nDone. Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    run_backfill()