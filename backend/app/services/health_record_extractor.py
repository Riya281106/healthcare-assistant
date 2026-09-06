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


        content = "Structured Symptom Record\n\n"


        # Symptoms

        content += "Symptoms:\n"

        if symptoms:

            for symptom in symptoms:

                content += f"- {symptom}\n"

        else:

            content += "- Not specifically identified\n"


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

            "record_content": content

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

        "record_content": record_content

    }