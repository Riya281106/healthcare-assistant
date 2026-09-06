import re


# ==================================================
# MEMORY EXTRACTION
# ==================================================

def extract_memories(message: str):

    """
    Extract important long-term health information
    from a user's message.

    Returns a list of memory dictionaries.
    """

    message_lower = message.lower()

    memories = []


    # ==================================================
    # ALLERGIES
    # ==================================================

    allergy_patterns = [

        r"i am allergic to (.+)",

        r"i'm allergic to (.+)",

        r"i have an allergy to (.+)",

        r"my allergy is (.+)"
    ]


    for pattern in allergy_patterns:

        match = re.search(
            pattern,
            message_lower
        )

        if match:

            allergy = match.group(1)

            allergy = clean_memory_text(allergy)

            if allergy:

                memories.append({

                    "memory_type": "ALLERGY",

                    "memory_content":
                        f"User is allergic to {allergy}"

                })

            break


    # ==================================================
    # MEDICAL CONDITIONS
    # ==================================================

    condition_patterns = [

        r"i have (diabetes)",

        r"i have (asthma)",

        r"i have (hypertension)",

        r"i have (high blood pressure)",

        r"i have (thyroid)",

        r"i have (pcos)",

        r"i have (migraine)",

        r"i have (heart disease)"
    ]


    for pattern in condition_patterns:

        match = re.search(
            pattern,
            message_lower
        )

        if match:

            condition = match.group(1)

            condition = clean_memory_text(condition)

            memories.append({

                "memory_type": "CONDITION",

                "memory_content":
                    f"User reports having {condition}"

            })

            break


    # ==================================================
    # MEDICATIONS
    # ==================================================

    medication_patterns = [

        r"i take (.+?) daily",

        r"i am taking (.+)",

        r"i'm taking (.+)",

        r"my medicine is (.+)"
    ]


    for pattern in medication_patterns:

        match = re.search(
            pattern,
            message_lower
        )

        if match:

            medication = match.group(1)

            medication = clean_memory_text(medication)

            if medication:

                memories.append({

                    "memory_type": "MEDICATION",

                    "memory_content":
                        f"User reports taking {medication}"

                })

            break


    return memories


# ==================================================
# CLEAN MEMORY TEXT
# ==================================================

def clean_memory_text(text: str):

    """
    Clean extracted memory text.
    """

    text = text.strip()

    text = re.sub(
        r"[.,!?]+$",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text