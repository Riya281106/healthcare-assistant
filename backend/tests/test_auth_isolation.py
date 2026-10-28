"""
Security tests: who can see / change whose data.
Each test here fails on the original code (which trusted a user_id sent by the browser).
"""

from app.core.database import save_health_record, save_message


# ---------- authentication required ----------

def test_chat_requires_login(client):
    assert client.post("/api/chat", json={"message": "hello"}).status_code == 401


def test_health_records_requires_login(client):
    assert client.get("/api/health-records").status_code == 401


def test_symptoms_requires_login(client):
    assert client.get("/api/symptoms").status_code == 401


def test_rag_stats_requires_login(client):
    assert client.get("/api/rag/stats").status_code == 401


def test_garbage_token_is_rejected(client):
    r = client.post("/api/chat", json={"message": "hi"}, headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


# ---------- user_id from the browser is ignored ----------

def test_chat_ignores_user_id_in_body(client, alice, bob):
    r = client.post(
        "/api/chat",
        json={"message": "hello there", "user_id": str(bob["id"])},   # alice pretends to be bob
        headers=alice["headers"],
    )
    assert r.status_code == 200

    history_alice = client.get("/api/conversations/history", headers=alice["headers"]).json()["history"]
    history_bob = client.get("/api/conversations/history", headers=bob["headers"]).json()["history"]

    assert len(history_alice) == 2          # user message + assistant reply
    assert history_bob == []                # nothing was written into bob's account


def test_old_unauthenticated_history_endpoint_is_gone(client, alice):
    save_message(str(alice["id"]), "user", "private message")
    r = client.get(f"/api/chat/history?user_id={alice['id']}")
    assert r.status_code == 404


# ---------- users cannot read each other's data ----------

def test_health_records_are_private(client, alice, bob):
    save_health_record(str(alice["id"]), "SYMPTOM", "alice has a private condition")

    mine = client.get("/api/health-records", headers=alice["headers"]).json()["records"]
    theirs = client.get(
        f"/api/health-records?user_id={alice['id']}",     # bob asks for alice's id
        headers=bob["headers"],
    ).json()["records"]

    assert len(mine) == 1
    assert theirs == []


def test_symptom_history_is_private(client, alice, bob):
    save_health_record(str(alice["id"]), "SYMPTOM", "x", symptom_name="headache")

    assert len(client.get("/api/symptoms", headers=alice["headers"]).json()["symptoms"]) == 1
    assert client.get(f"/api/symptoms?user_id={alice['id']}", headers=bob["headers"]).json()["symptoms"] == []


def test_conversation_history_is_private(client, alice, bob):
    save_message(str(alice["id"]), "user", "secret")
    assert client.get("/api/conversations/history", headers=bob["headers"]).json()["history"] == []


# ---------- admin-only reindex ----------

def test_reindex_forbidden_for_normal_user(client, alice):
    assert client.post("/api/rag/reindex", headers=alice["headers"]).status_code == 403


def test_reindex_requires_login(client):
    assert client.post("/api/rag/reindex").status_code == 401


def test_reindex_allowed_for_admin(client, admin, monkeypatch):
    import app.api.routes.rag as rag_routes
    monkeypatch.setattr(
        rag_routes, "load_knowledge_base",
        lambda force=False: {"total_chunks": 1, "files_processed": 1, "files_skipped": 0},
    )
    r = client.post("/api/rag/reindex", headers=admin["headers"])
    assert r.status_code == 200
    assert r.json()["total_chunks"] == 1


# ---------- input limits ----------

def test_empty_message_rejected(client, alice):
    assert client.post("/api/chat", json={"message": "   "}, headers=alice["headers"]).status_code == 422


def test_too_long_message_rejected(client, alice):
    r = client.post("/api/chat", json={"message": "a" * 2001}, headers=alice["headers"])
    assert r.status_code == 422


def test_message_at_limit_is_accepted(client, alice):
    r = client.post("/api/chat", json={"message": "a" * 2000}, headers=alice["headers"])
    assert r.status_code == 200


def test_very_long_password_rejected(client):
    r = client.post("/api/auth/register", json={"name": "X", "email": "x@example.com", "password": "p" * 129})
    assert r.status_code == 422


# ---------- rate limit ----------

def test_rate_limit_blocks_spam_but_never_an_emergency(client, alice, monkeypatch):
    codes = [
        client.post("/api/chat", json={"message": "hello"}, headers=alice["headers"]).status_code
        for _ in range(31)
    ]
    assert codes[:30] == [200] * 30
    assert codes[30] == 429

    # Now use the REAL orchestrator so the emergency reply is genuine.
    import app.main as main
    from app.services.agents.orchestrator import orchestrate
    monkeypatch.setattr(main, "orchestrate", orchestrate)

    emergency = client.post("/api/chat", json={"message": "I can\u2019t breathe"}, headers=alice["headers"])
    assert emergency.status_code == 200
    assert emergency.json()["urgency_tier"] == "emergency"


# ---------- normal behaviour still works ----------

def test_chat_response_shape(client, alice):
    data = client.post("/api/chat", json={"message": "hello"}, headers=alice["headers"]).json()
    assert data["response"] == "stub answer"
    for key in ["intent", "urgency_tier", "agent", "next_action", "rag_used", "sources"]:
        assert key in data
