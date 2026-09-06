from typing import Literal

from app.utils.emergency_detector import is_emergency


IntentType = Literal[
    "GENERAL_HEALTH",
    "SYMPTOM",
    "MEDICINE",
    "REPORT",
    "DIET_FITNESS",
    "HEALTH_RECORD",
    "REMINDER",
    "HOSPITAL",
    "MEMORY_RECALL",
    "EMERGENCY",
    "OTHER"
]


def classify_intent(message: str) -> IntentType:

    text = message.lower().strip()


    # ==================================================
    # 1. EMERGENCY
    # ==================================================

    if is_emergency(text):
        return "EMERGENCY"


    # ==================================================
    # 2. MEMORY RECALL
    # ==================================================

    memory_keywords = [

        # Direct memory questions
        "what do you remember about me",
        "what do you remember about my health",
        "what do you remember about my medical history",
        "what do you know about me",
        "what do you know about my health",

        # Saved information
        "what health information do you remember",
        "what health information do you remember about me",
        "what information have you saved about me",
        "what information do you have about me",
        "what have you saved about me",

        # Health memory
        "tell me my saved health information",
        "show my saved health information",
        "show my health information",
        "show my health details",
        "what are my health details",

        # Memories
        "show my memories",
        "my memories",
        "my saved information",
        "saved information about me",
        "saved health information",

        # Personal health context
        "do you remember my allergies",
        "do you remember my medication",
        "do you remember my medicines",
        "do you remember my condition",
        "what allergies do i have",
        "what medications do i take"
    ]


    if any(keyword in text for keyword in memory_keywords):
        return "MEMORY_RECALL"


    # ==================================================
    # 3. HEALTH RECORD
    # ==================================================

    health_record_keywords = [

        "health record",
        "health records",
        "health history",
        "my records",
        "my health data",
        "medical history",
        "my medical history",
        "health journal",
        "my journal",
        "add to my health record",
        "save to my health record",
        "update my health record"
    ]

    if any(keyword in text for keyword in health_record_keywords):
        return "HEALTH_RECORD"


    # ==================================================
    # 4. REMINDER
    # ==================================================

    reminder_keywords = [

        "remind me",
        "reminder",
        "set a reminder",
        "create a reminder",
        "schedule a reminder",
        "remember to",
        "cancel reminder",
        "delete reminder",
        "remove reminder",
        "show reminders",
        "my reminders",
        "list my reminders"
    ]

    if any(keyword in text for keyword in reminder_keywords):
        return "REMINDER"


    # ==================================================
    # 5. HOSPITAL
    # ==================================================

    hospital_keywords = [

        "hospital",
        "clinic",
        "doctor near me",
        "hospital near me",
        "nearest hospital",
        "nearby hospital",
        "find a doctor",
        "find hospital",
        "find a hospital",
        "nearby clinic",
        "emergency room"
    ]

    if any(keyword in text for keyword in hospital_keywords):
        return "HOSPITAL"


    # ==================================================
    # 6. REPORT
    # ==================================================

    report_keywords = [

        "medical report",
        "blood report",
        "test report",
        "lab report",
        "blood test",
        "scan report",
        "medical test",
        "test results",
        "lab results",
        "diagnostic report",
        "x ray report",
        "mri report",
        "ct scan report"
    ]

    if any(keyword in text for keyword in report_keywords):
        return "REPORT"


    # ==================================================
    # 7. SYMPTOM
    # ==================================================

    symptom_keywords = [

        "symptom",
        "symptoms",
        "pain",
        "fever",
        "headache",
        "cough",
        "cold",
        "vomiting",
        "nausea",
        "dizziness",
        "fatigue",
        "sore throat",
        "stomach ache",
        "stomach pain",
        "body pain",
        "weakness",
        "rash",
        "diarrhea",
        "constipation",
        "chills",
        "infection",
        "breathing problem"
    ]

    if any(keyword in text for keyword in symptom_keywords):
        return "SYMPTOM"


    # ==================================================
    # 8. MEDICINE
    # ==================================================

    medicine_keywords = [

        "medicine",
        "medication",
        "tablet",
        "capsule",
        "paracetamol",
        "ibuprofen",
        "dose",
        "dosage",
        "drug",
        "side effect",
        "side effects",
        "drug interaction",
        "contraindication",
        "antibiotic",
        "prescription"
    ]

    if any(keyword in text for keyword in medicine_keywords):
        return "MEDICINE"


    # ==================================================
    # 9. DIET / FITNESS
    # ==================================================

    diet_keywords = [

        "diet",
        "nutrition",
        "food",
        "exercise",
        "workout",
        "fitness",
        "weight loss",
        "healthy meal",
        "healthy diet",
        "stay fit",
        "physical activity",
        "lose weight",
        "gain weight",
        "meal plan"
    ]

    if any(keyword in text for keyword in diet_keywords):
        return "DIET_FITNESS"


    # ==================================================
    # 10. GENERAL HEALTH
    # ==================================================

    general_health_keywords = [

        "health",
        "healthy",
        "disease",
        "condition",
        "prevention",
        "wellness"
    ]

    if any(keyword in text for keyword in general_health_keywords):
        return "GENERAL_HEALTH"


    return "OTHER"