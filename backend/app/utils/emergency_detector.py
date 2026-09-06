# ==================================================
# EMERGENCY DETECTOR
# ==================================================

EMERGENCY_KEYWORDS = [

    "chest pain",
    "severe chest pain",
    "heart attack",
    "heart is hurting",

    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "unable to breathe",
    "not breathing",

    "stroke",
    "face drooping",
    "sudden weakness",
    "unable to speak",
    "slurred speech",
    "severe confusion",

    "severe bleeding",
    "bleeding heavily",
    "uncontrolled bleeding",
    "major injury",

    "unconscious",
    "passed out",
    "fainted and not waking",
    "seizure",
    "choking",

    "overdose",
    "poisoned",
    "swallowed poison",

    "suicide",
    "kill myself",
    "want to die",
    "self harm",
    "hurt myself"

]


# --------------------------------------------------
# NEGATION WORDS
# If one of these appears shortly before a matched
# keyword, the user is likely DENYING the symptom,
# not reporting it.
# --------------------------------------------------

NEGATION_WORDS = [
    "no", "not", "dont", "don't", "doesnt", "doesn't",
    "never", "without", "isnt", "isn't", "arent", "aren't",
    "wasnt", "wasn't", "havent", "haven't", "hadnt", "hadn't"
]


def _is_negated_match(
    lowered_text: str,
    keyword: str,
    window: int = 4
) -> bool:

    """
    Checks whether the matched keyword is immediately preceded
    by a negation word within a few words, meaning the user is
    denying the symptom rather than reporting it.

    This is a simple heuristic, not perfect NLP — but it prevents
    the most common and dangerous false-positive pattern:
    "I don't have chest pain" being flagged the same as
    "I have chest pain".
    """

    index = lowered_text.find(keyword)

    if index == -1:
        return False

    preceding_text = lowered_text[:index]
    preceding_words = preceding_text.strip().split()
    nearby_words = preceding_words[-window:]

    for word in nearby_words:

        cleaned = word.strip(".,!?")

        if cleaned in NEGATION_WORDS:
            return True

    return False


# ==================================================
# CHECK EMERGENCY
# ==================================================

def is_emergency(message: str) -> bool:

    if not message:
        return False

    lowered = message.lower().strip()

    for keyword in EMERGENCY_KEYWORDS:

        if keyword in lowered:

            if _is_negated_match(lowered, keyword):
                continue

            return True

    return False