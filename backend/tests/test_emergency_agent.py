from app.services.agents.emergency_agent import run_emergency_agent
from app.utils.emergency_detector import detect_emergency


def reply(message):
    return run_emergency_agent(message, detect_emergency(message))


def test_medical_emergency_gives_112_and_108():
    r = reply("my dad has chest pain")
    assert r["urgency_tier"] == "emergency"
    assert "112" in r["response"]
    assert "108" in r["response"]
    assert r["agent"] == "EMERGENCY_AGENT"
    assert r["rag_used"] is False


def test_self_harm_gives_tele_manas_and_112():
    text = reply("I want to kill myself")["response"]
    assert "14416" in text
    assert "1800-891-4416" in text
    assert "112" in text


def test_overdose_with_intent_gets_both_messages():
    text = reply("I took too many sleeping pills to end my life")["response"]
    assert "112" in text
    assert "14416" in text


def test_first_aid_matches_category():
    assert "press firmly" in reply("bleeding heavily from my arm")["response"].lower()
    assert "note the exact time" in reply("my mom has slurred speech")["response"].lower()
    assert "adrenaline" in reply("my throat is closing after eating peanuts")["response"].lower()


def test_response_never_tells_user_to_take_medicine():
    for message in ["my dad has chest pain", "I can't breathe", "bleeding heavily"]:
        text = reply(message)["response"].lower()
        assert "take aspirin" not in text
        assert "take a tablet" not in text


def test_works_without_an_assessment():
    r = run_emergency_agent("anything")
    assert "112" in r["response"]
