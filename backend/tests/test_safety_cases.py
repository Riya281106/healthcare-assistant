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
