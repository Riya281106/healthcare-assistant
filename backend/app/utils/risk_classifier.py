# ==================================================
# RISK CLASSIFIER
#
# This module's only job: look at a message and decide
# how urgent it is, BEFORE any AI or agent runs.
#
# It returns one of exactly four tiers:
#   "EMERGENCY"  - needs help right now
#   "URGENT"     - needs a doctor soon, not immediately dangerous
#   "SELF_CARE"  - low risk, manageable at home
#   "GENERAL"    - information question, no personal risk
# ==================================================

from app.utils.emergency_detector import is_emergency

RISK_TIERS = [
    "EMERGENCY",
    "URGENT",
    "SELF_CARE",
    "GENERAL"
]


# --------------------------------------------------
# URGENT KEYWORDS
# Symptoms that are not immediately life-threatening
# but genuinely warrant seeing a doctor soon.
# --------------------------------------------------

URGENT_KEYWORDS = [
    "fever for 3 days",
    "fever for three days",
    "fever for more than 3 days",
    "high fever",
    "worsening pain",
    "getting worse",
    "not getting better",
    "won't stop bleeding",
    "persistent vomiting",
    "severe pain",
    "blood in stool",
    "blood in urine",
    "blood in vomit",
    "coughing blood",
    "severe headache",
    "swelling that is spreading",
    "rash spreading",
    "unable to keep food down",
    "dehydrated",
    "signs of infection"
]


# --------------------------------------------------
# SELF-CARE KEYWORDS
# Mild, common symptoms the user is describing about
# themselves, with no danger or urgency signal present.
# --------------------------------------------------

SELF_CARE_KEYWORDS = [
    "mild headache",
    "slight headache",
    "small headache",
    "headache",
    "runny nose",
    "mild cold",
    "sore throat",
    "mild cough",
    "cough",
    "tired",
    "fatigue",
    "mild fever",
    "low fever",
    "stomach ache",
    "mild stomach pain",
    "nausea",
    "mild nausea",
    "muscle ache",
    "body ache",
    "sneezing",
    "stuffy nose",
    "mild pain",
    "slight pain"
]


def is_urgent(message: str) -> bool:

    lowered = message.lower().strip()

    for keyword in URGENT_KEYWORDS:

        if keyword in lowered:
            return True

    return False


def is_self_care(message: str) -> bool:

    lowered = message.lower().strip()

    for keyword in SELF_CARE_KEYWORDS:

        if keyword in lowered:
            return True

    return False


def classify_risk(message: str) -> str:

    # ----------------------------------------
    # TIER 1: EMERGENCY
    # ----------------------------------------

    if is_emergency(message):
        return "EMERGENCY"

    # ----------------------------------------
    # TIER 2: URGENT
    # ----------------------------------------

    if is_urgent(message):
        return "URGENT"

    # ----------------------------------------
    # TIER 3: SELF_CARE
    # ----------------------------------------

    if is_self_care(message):
        return "SELF_CARE"

    # ----------------------------------------
    # TIER 4: GENERAL
    # Nothing above matched — treat as a general
    # information question, not a personal symptom.
    # ----------------------------------------

    return "GENERAL"