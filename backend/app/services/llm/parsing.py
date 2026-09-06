import re
from typing import Tuple

VALID_TIERS = {"emergency", "see_doctor", "self_care"}

_TIER_PATTERN = re.compile(
    r'^\[TIER:\s*(emergency|see_doctor|self_care)\]\s*',
    re.IGNORECASE,
)


def parse_urgency_tier(raw_text: str) -> Tuple[str, str]:
    """
    Extracts the urgency tier tag from the model's raw response.
    Falls back to the safest tier ("self_care" is NOT used as the
    fallback here on purpose -- see note below) if parsing fails.
    """
    if not raw_text or not raw_text.strip():
        # Model returned nothing usable -- do not guess self_care silently.
        return "see_doctor", (
            "Sorry, I wasn't able to process that properly. "
            "If this is urgent, please contact a doctor or emergency "
            "services directly."
        )

    match = _TIER_PATTERN.match(raw_text)
    if match:
        tier = match.group(1).lower()
        if tier in VALID_TIERS:
            return tier, raw_text[match.end():].strip()

    # Tag missing or malformed -- conservative fallback.
    return "see_doctor", raw_text.strip()
    