import pytest

from app.utils.emergency_detector import detect_emergency
from safety_cases import BENIGN, EMERGENCY


@pytest.mark.parametrize("text,category", EMERGENCY)
def test_real_emergency_is_detected(text, category):
    found = detect_emergency(text)
    assert found is not None, f"MISSED: {text!r}"
    assert category in found.categories, f"{text!r}: expected {category}, got {found.categories}"


@pytest.mark.parametrize("text", BENIGN)
def test_harmless_message_is_not_flagged(text):
    assert detect_emergency(text) is None, f"FALSE ALARM: {text!r}"


def test_new_categories_have_first_aid_text():
    from app.services.agents.emergency_agent import build_emergency_text

    for message, key in [("snake bite", "anti-snake venom"), ("he is drowning", "CPR"), ("fever in a newborn", "baby")]:
        assert key in build_emergency_text(detect_emergency(message), "en")


def test_first_aid_matches_the_kind_of_bleeding():
    from app.services.agents.emergency_agent import build_emergency_text

    vomit = build_emergency_text(detect_emergency("vomiting blood"), "en")
    assert "don't eat or drink" in vomit and "press firmly on the wound" not in vomit
    pregnant = build_emergency_text(detect_emergency("I am pregnant and bleeding"), "en")
    assert "lie down on your side" in pregnant and "press firmly on the wound" not in pregnant
    wound = build_emergency_text(detect_emergency("bleeding heavily from my leg"), "en")
    assert "press firmly on the wound" in wound
    baby = build_emergency_text(detect_emergency("my 2 month old has fever"), "en")
    assert "take the baby to the nearest hospital" in baby and "avoid driving yourself" not in baby


import pytest as _pytest


@_pytest.mark.parametrize("text", [
    "I have had a fever for 4 days", "fever for 5 days", "fever since 4 days", "i have fever from last 4 days",
    "temperature for three days", "fever for 10 days",
])
def test_a_fever_lasting_three_or_more_days_is_urgent(text):
    from app.utils.risk_classifier import classify_risk
    assert classify_risk(text) == "URGENT"


@_pytest.mark.parametrize("text", ["I had a fever for 1 day", "fever for 2 days", "what is a fever?", "mild fever since morning"])
def test_a_short_fever_is_not_urgent(text):
    from app.utils.risk_classifier import classify_risk
    assert classify_risk(text) != "URGENT"

