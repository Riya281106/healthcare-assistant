import re


# ==================================================
# SYMPTOM EXTRACTION
# ==================================================

def extract_symptoms(message: str):

    """
    Extract common symptoms from user message.
    """

    message_lower = message.lower()

    known_symptoms = [

        "headache",
        "headaches",

        "dizziness",
        "dizzy",

        "fever",

        "cough",

        "cold",

        "sore throat",

        "nausea",

        "vomiting",

        "stomach pain",

        "abdominal pain",

        "chest pain",

        "back pain",

        "fatigue",

        "weakness",

        "shortness of breath",

        "difficulty breathing"

    ]


    detected_symptoms = []

    for symptom in known_symptoms:

        if symptom in message_lower:

            # Avoid duplicate variations
            normalized = symptom

            if symptom == "headaches":
                normalized = "headache"

            elif symptom == "dizzy":
                normalized = "dizziness"

            if normalized not in detected_symptoms:

                detected_symptoms.append(normalized)


    return detected_symptoms


# ==================================================
# DURATION EXTRACTION
# ==================================================

def extract_duration(message: str):

    """
    Extract duration such as:
    two days
    3 days
    for a week
    since yesterday
    """

    message_lower = message.lower()


    patterns = [

        r'for\s+\d+\s+(?:day|days|week|weeks|month|months)',

        r'for\s+(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:day|days|week|weeks|month|months)',

        r'since\s+(?:yesterday|morning|last night)',

        r'(?:since|from)\s+\d+\s+(?:day|days|week|weeks|month|months)\s+ago'

    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            message_lower
        )

        if match:

            return match.group(0)


    return None


# ==================================================
# SEVERITY EXTRACTION
# ==================================================

def extract_severity(message: str):

    """
    Extract a severity indicator from the user message.

    Detects three styles:
    - numeric scale: "7/10", "8 out of 10"
    - descriptive keyword: mild / moderate / severe / unbearable
    - comparative trend: "worse than yesterday", "getting better"

    Returns a short human-readable severity string, or None if no
    severity signal was found.
    """

    message_lower = message.lower()


    # ----------------------------------------------
    # NUMERIC SCALE (e.g. "7/10", "8 out of 10")
    # ----------------------------------------------

    numeric_match = re.search(
        r'\b(\d{1,2})\s*(?:/|out of)\s*10\b',
        message_lower
    )

    if numeric_match:

        score = int(numeric_match.group(1))

        if score <= 3:
            label = "mild"
        elif score <= 6:
            label = "moderate"
        else:
            label = "severe"

        return f"{score}/10 ({label})"


    # ----------------------------------------------
    # COMPARATIVE TREND
    # ----------------------------------------------

    worsening_patterns = [
        "worse than yesterday",
        "worse than last week",
        "getting worse",
        "worsening",
        "worse today",
    ]

    improving_patterns = [
        "better than yesterday",
        "better than last week",
        "getting better",
        "improving",
        "better today",
    ]

    for pattern in worsening_patterns:
        if pattern in message_lower:
            return "worsening"

    for pattern in improving_patterns:
        if pattern in message_lower:
            return "improving"


    # ----------------------------------------------
    # DESCRIPTIVE KEYWORDS
    # ----------------------------------------------

    if any(word in message_lower for word in ["unbearable", "excruciating", "extreme"]):
        return "severe"

    if any(word in message_lower for word in ["severe", "intense", "very bad", "very painful"]):
        return "severe"

    if "moderate" in message_lower:
        return "moderate"

    if any(word in message_lower for word in ["mild", "slight", "a little"]):
        return "mild"


    return None


# ==================================================
# HEALTH RECORD EXTRACTION
# ==================================================

def extract_health_record(
    user_message: str,
    ai_response: str,
    intent: str
):

    """
    Extract meaningful healthcare information
    from a user interaction.

    Returns structured health record
    or None if the interaction should not
    be stored.
    """


    # ==========================================
    # RECORDABLE INTENTS
    # ==========================================

    recordable_intents = [

        "SYMPTOM",

        "URGENT",

        "SELF_CARE",

        "MEDICINE",

        "REPORT",

        "DIET_FITNESS"

    ]


    if intent not in recordable_intents:

        return None


    # ==========================================
    # SYMPTOM RECORD
    # ==========================================

    if intent in ("SYMPTOM", "URGENT", "SELF_CARE"):

        symptoms = extract_symptoms(
            user_message
        )

        duration = extract_duration(
            user_message
        )

        severity = extract_severity(
            user_message
        )


        content = "Structured Symptom Record\n\n"


        # Symptoms

        content += "Symptoms:\n"

        if symptoms:

            for symptom in symptoms:

                content += f"- {symptom}\n"

        else:

            content += "- Not specifically identified\n"


        # Severity

        content += "\nSeverity:\n"

        if severity:

            content += f"- {severity}\n"

        else:

            content += "- Not specified\n"


        # Duration

        content += "\nDuration:\n"

        if duration:

            content += f"- {duration}\n"

        else:

            content += "- Not specified\n"


        # Original Message

        content += "\nOriginal User Message:\n"

        content += f"{user_message}\n"


        # AI Response

        content += "\nAI Response:\n"

        content += f"{ai_response}"


        return {

            "record_type": intent,

            "record_content": content,

            "symptom_name": ", ".join(symptoms) if symptoms else None,

            "severity": severity,

            "duration_text": duration

        }


    # ==========================================
    # OTHER HEALTH RECORD TYPES
    # ==========================================

    record_content = (

        f"User Query: {user_message}\n\n"

        f"AI Response: {ai_response}"

    )


    return {

        "record_type": intent,

        "record_content": record_content,

        "symptom_name": None,

        "severity": None,

        "duration_text": None

    }
