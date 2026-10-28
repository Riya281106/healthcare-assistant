"""
Shared test setup.

* Fake secrets are set BEFORE the app is imported (the app refuses to start
  without SECRET_KEY / GROQ_API_KEY).
* Every test gets a fresh temporary SQLite database; your real healthcare.db
  is never touched.
* The LLM is replaced with a stub, so tests need no API key and no network.
"""

import os
import sys

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ["ADMIN_EMAILS"] = "admin@example.com"

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import app.core.database as database
    monkeypatch.setattr(database, "DATABASE_NAME", str(tmp_path / "test.db"))
    database.init_db()

    import app.main as main
    main.chat_limiter.reset()

    # Stub the AI so non-emergency chats never hit the network.
    def fake_orchestrate(message, history=None, user_id=None, ui_language=None):
        return {
            "response": "stub answer",
            "intent": "GENERAL",
            "urgency_tier": "general",
            "agent": "GENERAL_AGENT",
            "next_action": "GENERAL_AGENT",
            "rag_used": False,
            "sources": [],
        }
    monkeypatch.setattr(main, "orchestrate", fake_orchestrate)

    # No `with` block on purpose: skips the startup event (which loads the
    # vector store and would try to download an embedding model).
    return TestClient(main.app)


def register(client, name, email, password="password123"):
    response = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return {
        "id": data["user"]["id"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture()
def alice(client):
    return register(client, "Alice", "alice@example.com")


@pytest.fixture()
def bob(client):
    return register(client, "Bob", "bob@example.com")


@pytest.fixture()
def admin(client):
    return register(client, "Admin", "admin@example.com")
