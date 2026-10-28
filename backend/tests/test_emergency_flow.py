"""End-to-end: the real orchestrator + emergency agent behind the real API (LLM never called)."""

import pytest


@pytest.mark.parametrize("message", [
    "I can\u2019t breathe",
    "no fever but chest pain",
    "I want to end my life",
    "my dad has slurred speech",
])
def test_emergency_message_gets_emergency_reply(client, alice, message, monkeypatch):
    import app.main as main
    # Use the REAL orchestrator here, not the stub.
    from app.services.agents.orchestrator import orchestrate
    monkeypatch.setattr(main, "orchestrate", orchestrate)

    r = client.post("/api/chat", json={"message": message}, headers=alice["headers"])
    data = r.json()

    assert r.status_code == 200
    assert data["urgency_tier"] == "emergency"
    assert data["intent"] == "EMERGENCY"
    assert data["agent"] == "EMERGENCY_AGENT"
    assert "112" in data["response"]


def test_emergency_reply_still_works_when_orchestrator_crashes(client, alice, monkeypatch):
    import app.main as main

    def boom(**kwargs):
        raise RuntimeError("LLM provider is down")
    monkeypatch.setattr(main, "orchestrate", boom)

    r = client.post("/api/chat", json={"message": "I can't breathe"}, headers=alice["headers"])
    assert r.status_code == 200
    assert r.json()["urgency_tier"] == "emergency"
    assert "112" in r.json()["response"]


def test_non_emergency_crash_returns_clean_503_without_internals(client, alice, monkeypatch):
    import app.main as main

    def boom(**kwargs):
        raise RuntimeError("secret internal detail xyz")
    monkeypatch.setattr(main, "orchestrate", boom)

    r = client.post("/api/chat", json={"message": "hello"}, headers=alice["headers"])
    assert r.status_code == 503
    assert "secret internal detail" not in r.text


def test_emergency_still_replies_when_history_lookup_fails(client, alice, monkeypatch):
    import app.main as main
    from app.services.agents.orchestrator import orchestrate
    monkeypatch.setattr(main, "orchestrate", orchestrate)

    def broken(**kwargs):
        raise RuntimeError("db hiccup")
    monkeypatch.setattr(main, "get_recent_messages", broken)

    r = client.post("/api/chat", json={"message": "I can't breathe"}, headers=alice["headers"])
    assert r.status_code == 200
    assert r.json()["urgency_tier"] == "emergency"


def test_bookkeeping_failure_does_not_lose_the_answer(client, alice, monkeypatch):
    import app.main as main

    def broken(**kwargs):
        raise RuntimeError("disk full")
    monkeypatch.setattr(main, "save_message", broken)

    r = client.post("/api/chat", json={"message": "hello"}, headers=alice["headers"])
    assert r.status_code == 200
    assert r.json()["response"] == "stub answer"
