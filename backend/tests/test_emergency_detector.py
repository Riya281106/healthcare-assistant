import pytest

from app.utils.emergency_detector import detect_emergency, is_emergency


# (message, should_fire)
EMERGENCIES = [
    "I have chest pain",
    "severe chest pain since morning",
    "my chest feels very tight",
    "pain spreading to my left arm and jaw",
    "I think I'm having a heart attack",
    "I can't breathe",
    "I can\u2019t breathe",                      # curly apostrophe (phone default)
    "CANT BREATHE!!!",
    "cannot breathe properly",
    "I am short of breath and my lips are turning blue",
    "my baby is not breathing",
    "difficulty breathing since last night",
    "she may have had a stroke",
    "my mom has slurred speech",
    "his face is drooping on one side",
    "sudden weakness in my left arm",
    "worst headache of my life",
    "bleeding heavily from my leg",
    "the bleeding won't stop",
    "he is unconscious",
    "she collapsed in the kitchen",
    "he is having a seizure",
    "my son is choking",
    "I took too many sleeping pills",
    "she swallowed poison",
    "my throat is closing after eating peanuts",
    "I want to kill myself",
    "I want to end my life",
    "I am feeling suicidal",
    "I don\u2019t want to live anymore",
    "I want to hurt myself",
    "I keep cutting myself",
    # negation must not hide a real symptom
    "no fever but chest pain",
    "I have no chest pain but my dad can't breathe",
    "no cough, chest pain since morning",
    "not sure if I want to die",
    "I do not know if this is a heart attack",
    "no one would care if I kill myself",
    # Hinglish / Hindi
    "seene mein dard ho raha hai",
    "mujhe saans nahi aa rahi",
    "mujhe marna chahta hun",
    "\u092e\u0941\u091d\u0947 \u0938\u0940\u0928\u0947 \u092e\u0947\u0902 \u0926\u0930\u094d\u0926 \u0939\u0948",   # seene mein dard (Devanagari)
    "\u0906\u0924\u094d\u092e\u0939\u0924\u094d\u092f\u093e \u0915\u0947 \u0935\u093f\u091a\u093e\u0930 \u0906 \u0930\u0939\u0947 \u0939\u0948\u0902",  # suicidal thoughts
]

NOT_EMERGENCIES = [
    "I have a sore throat and mild headache",
    "I have a runny nose and a mild cold",
    "I don't have chest pain",
    "I don\u2019t have chest pain",
    "no chest pain, no shortness of breath",
    "denies chest pain",
    "without any bleeding",
    "I can't breathe through my nose, I have a cold",
    "keystroke logging error in my code",
    "I have a brushstroke style painting",
    "What are the symptoms of a heart attack?",
    "how do I prevent a stroke",
    "no family history of heart attack",
    "I cut myself shaving",
    "I hurt myself playing cricket",
    "I think I got food poisoning",
    "I took too many photos today",
    "can't talk right now, I'm in a meeting",
    "I don't want to die",
    "what is the difference between a heart attack and cardiac arrest",
    "I want to book a doctor appointment",
    "remind me to take my tablet at 8pm",
    "",
    "   ",
]


@pytest.mark.parametrize("message", EMERGENCIES)
def test_emergencies_are_detected(message):
    assert detect_emergency(message) is not None, f"MISSED emergency: {message!r}"
    assert is_emergency(message) is True


@pytest.mark.parametrize("message", NOT_EMERGENCIES)
def test_non_emergencies_are_not_flagged(message):
    assert detect_emergency(message) is None, f"false alarm: {message!r}"


def test_assessment_reports_category_and_rule():
    a = detect_emergency("my dad has chest pain")
    assert a.primary_category == "CARDIAC"
    assert "chest_pain" in a.rule_ids


def test_overdose_with_intent_reports_both_categories():
    a = detect_emergency("I took too many sleeping pills to end my life")
    assert "POISONING" in a.categories
    assert a.has_self_harm is True


def test_none_and_empty_input_are_safe():
    assert detect_emergency(None) is None
    assert is_emergency(None) is False
