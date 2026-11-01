"""
Appointment-request flow, Maharashtra-only scope, privacy and security controls.
Everything runs against a temporary database with stubbed hospital search; no network.
"""

import re
import sqlite3
from datetime import date

import pytest

import app.core.database as database
import app.services.agents.appointment_flow as flow
import app.services.agents.care_navigator as nav
from app.core.config import settings
from app.services.integrations.google_places import PlacesUnavailable
from app.services.integrations.osm_places import OutsideMaharashtra

# Fixtures and helpers shared with the older navigation tests.
from test_care_navigation import (  # noqa: F401  (fixtures are used by name)
    chat,
    llm,
    make_places,
    no_real_network,
    places,
    real,
)

TODAY = date(2026, 10, 31)   # a Saturday


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(flow, "today", lambda: TODAY)


def start_booking(real, user, hospital=2):
    """Search, choose a hospital, say yes: returns the first form question."""
    chat(real, user, "Find eye hospitals near 400001")
    chosen = chat(real, user, f"book hospital {hospital}")
    assert "appointment request" in chosen["response"]
    return chat(real, user, "yes")


def fill_form(real, user, name="Riya Sharma", phone="98765 43210", age="21", when="tomorrow morning", reason="eye pain for two days"):
    chat(real, user, name)
    chat(real, user, phone)
    chat(real, user, age)
    chat(real, user, when)
    return chat(real, user, reason)       # the summary


def db_rows(client, table="appointments"):
    conn = sqlite3.connect(database.DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# Maharashtra only
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("pin", ["110001", "560001", "380001", "403001", "700001"])
def test_pin_outside_maharashtra_is_refused_and_nothing_is_searched(real, alice, places, pin):
    data = chat(real, alice, f"Find eye hospitals near {pin}")
    assert "Maharashtra" in data["response"]
    assert data["facilities"] == []
    assert places.queries == []


@pytest.mark.parametrize("pin", ["400001", "411001", "440001", "422001", "431001", "416001"])
def test_maharashtra_pins_are_searched(real, alice, places, pin):
    data = chat(real, alice, f"Find eye hospitals near {pin}")
    assert data["ui"] == "facility_results" and places.queries


def test_locality_outside_maharashtra_is_refused(real, alice, monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)

    def outside(*a, **k):
        raise OutsideMaharashtra("Indiranagar")
    monkeypatch.setattr(nav, "osm_search", outside)
    data = chat(real, alice, "Find eye hospitals near Indiranagar, Bangalore")
    assert "Maharashtra" in data["response"] and data["facilities"] == []
    # and the person can simply try again with a Maharashtra place
    monkeypatch.setattr(nav, "osm_search", lambda *a, **k: [{"name": "Pune Eye Care", "address": "Pune 411001", "phone": None, "website": None,
                                                              "maps_url": "https://m/1", "place_id": "n/1", "source": "OpenStreetMap", "distance_km": 1.2,
                                                              "lat": 18.52, "lon": 73.85, "specialty_match": True}])
    data = chat(real, alice, "411001")
    assert data["ui"] == "facility_results" and data["facilities"][0]["name"] == "Pune Eye Care"


# ----------------------------------------------------------------------------
# 10 results, directions, phone fallback
# ----------------------------------------------------------------------------

def test_results_have_directions_and_a_phone_fallback_link(real, alice, places):
    places.places = make_places(4)
    places.places[1]["phone"] = None
    data = chat(real, alice, "Find eye hospitals near 400001")
    first, second = data["facilities"][0], data["facilities"][1]
    assert first["phone"] and first["phone_lookup_url"] is None
    assert second["phone"] is None and second["phone_lookup_url"].startswith("https://www.google.com/maps/search/")
    assert "Phone: not listed" in data["response"]
    assert "Ranked nearest first" in data["response"]
    assert data["trace"] and any("Maharashtra" in t for t in data["trace"])


def test_general_hospitals_used_as_filler_are_labelled(real, alice, monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    rows = []
    for i in range(1, 11):
        rows.append({"name": f"Hospital {i}", "address": None, "phone": None, "website": None, "maps_url": "https://m",
                     "place_id": f"n/{i}", "source": "OpenStreetMap", "distance_km": float(i), "lat": 19.0, "lon": 72.8,
                     "specialty_match": i <= 2})
    monkeypatch.setattr(nav, "osm_search", lambda *a, **k: rows)
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert len(data["facilities"]) == 10
    assert data["facilities"][0]["specialty_match"] is True
    assert "department not confirmed" in data["facilities"][5]["specialty"]
    assert "general hospitals" in data["response"]


# ----------------------------------------------------------------------------
# Full appointment flow with a real (non-demo) hospital
# ----------------------------------------------------------------------------

def test_full_flow_saves_a_request_and_never_claims_it_is_booked(real, alice, places):
    first_question = start_booking(real, alice)
    assert "Step 1 of 5" in first_question["response"] and "CANCEL" in first_question["response"]

    summary = fill_form(real, alice)
    assert summary["ui"] == "appointment_summary"
    assert "Riya Sharma" in summary["response"] and "Sun 1 Nov 2026, morning" in summary["response"]
    assert "+91 98765 43210" in summary["response"]
    assert db_rows(real) == []                                   # nothing saved before YES

    done = chat(real, alice, "yes")
    assert done["ui"] == "appointment_confirmed"
    ref = done["appointment"]["ref"]
    assert re.fullmatch(r"HA-[A-Z2-9]{6}", ref)
    text = done["response"]
    assert "REQUESTED" in text and "NOT confirmed" in text
    assert "+91 22 0000 0002" in text                            # call the hospital to confirm
    assert "https://www.google.com/maps/dir/" in text           # directions
    assert "booked" not in text.lower().replace("not booked", "")
    assert done["appointment"]["status"] == "requested"

    rows = db_rows(real)
    assert len(rows) == 1 and rows[0]["status"] == "requested"
    # personal details are encrypted at rest
    for column in ("patient_name", "patient_phone", "reason"):
        assert rows[0][column].startswith("enc1:")
        assert "Riya" not in rows[0][column] and "98765" not in rows[0][column]
    # a readable audit trail exists
    events = db_rows(real, "appointment_events")
    assert [e["event"] for e in events] == ["created as requested"]


def test_owner_can_list_and_nobody_else_can_see_or_cancel(real, alice, bob, places):
    start_booking(real, alice)
    fill_form(real, alice)
    ref = chat(real, alice, "yes")["appointment"]["ref"]

    mine = real.get("/api/appointments", headers=alice["headers"]).json()["appointments"]
    assert len(mine) == 1 and mine[0]["patient_name"] == "Riya Sharma"      # decrypted for the owner
    assert real.get("/api/appointments", headers=bob["headers"]).json()["appointments"] == []
    assert real.post(f"/api/appointments/{ref}/cancel", headers=bob["headers"]).status_code == 404
    assert real.get("/api/appointments").status_code in (401, 403)
    assert db_rows(real)[0]["status"] == "requested"

    # Bob cannot even see it through chat
    chat(real, bob, "Find eye hospitals near 400001")
    assert "can't find" in chat(real, bob, f"cancel appointment {ref}")["response"]


def test_cancel_through_chat_needs_a_yes(real, alice, places):
    start_booking(real, alice)
    fill_form(real, alice)
    ref = chat(real, alice, "yes")["appointment"]["ref"]

    ask = chat(real, alice, f"cancel appointment {ref}")
    assert "Reply YES" in ask["response"]
    assert db_rows(real)[0]["status"] == "requested"            # not cancelled yet
    assert "cancelled" in chat(real, alice, "yes")["response"]
    assert db_rows(real)[0]["status"] == "cancelled"
    assert "already cancelled" in chat(real, alice, f"cancel appointment {ref}")["response"]


def test_my_appointments_lists_own_requests(real, alice, places):
    assert "don't have any" in chat(real, alice, "my appointments")["response"]
    start_booking(real, alice)
    fill_form(real, alice)
    chat(real, alice, "yes")
    data = chat(real, alice, "show my appointments")
    assert "REQUESTED" in data["response"] and "Eye Care Hospital 2" in data["response"]


def test_stopping_saves_nothing(real, alice, places):
    start_booking(real, alice)
    chat(real, alice, "Riya Sharma")
    data = chat(real, alice, "cancel")
    assert "Nothing was saved" in data["response"]
    assert db_rows(real) == []


def test_saying_no_to_the_offer_returns_to_the_list(real, alice, places):
    chat(real, alice, "Find eye hospitals near 400001")
    chat(real, alice, "book hospital 2")
    data = chat(real, alice, "no")
    assert "No problem" in data["response"] and db_rows(real) == []
    again = chat(real, alice, "3")                                  # numbers still work afterwards
    assert again["facilities"][0]["name"] == "Eye Care Hospital 3"


def test_changing_one_detail_returns_to_the_summary(real, alice, places):
    start_booking(real, alice)
    fill_form(real, alice)
    asked = chat(real, alice, "change the phone number")
    assert "Which mobile number" in asked["response"]
    summary = chat(real, alice, "91234 56789")
    assert "+91 91234 56789" in summary["response"] and summary["ui"] == "appointment_summary"
    assert db_rows(real) == []


# ----------------------------------------------------------------------------
# Validation: one question at a time, never advance on a bad answer
# ----------------------------------------------------------------------------

def test_bad_answers_are_re_asked(real, alice, places):
    start_booking(real, alice)
    assert "doesn't look like a name" in chat(real, alice, "12345")["response"]
    chat(real, alice, "Riya Sharma")
    assert "10-digit" in chat(real, alice, "12345")["response"]
    assert "10-digit" in chat(real, alice, "5876543210")["response"]          # must start with 6-9
    chat(real, alice, "+91 98765-43210")
    assert "age" in chat(real, alice, "two hundred")["response"].lower()
    assert "doesn't look right" in chat(real, alice, "200")["response"]
    chat(real, alice, "21")
    assert "already passed" in chat(real, alice, "yesterday")["response"]
    assert "Which day" in chat(real, alice, "10 am")["response"]
    assert "60 days" in chat(real, alice, "5 jan 2027")["response"]
    assert "Step 5 of 5" in chat(real, alice, "tomorrow evening")["response"]


@pytest.mark.parametrize("text,expected", [
    ("tomorrow morning", (date(2026, 11, 1), "morning")),
    ("5 Nov evening", (date(2026, 11, 5), "evening")),
    ("Monday 11am", (date(2026, 11, 2), "11:00 AM")),
    ("15/11", (date(2026, 11, 15), None)),
    ("day after tomorrow", (date(2026, 11, 2), None)),
    ("today", (date(2026, 10, 31), None)),
])
def test_date_parser(text, expected):
    d, slot, error = flow.parse_when(text, TODAY)
    assert error is None and (d, slot) == expected


def test_sql_looking_input_is_stored_as_plain_text(real, alice, places):
    start_booking(real, alice)
    summary = fill_form(real, alice, reason="x'); DROP TABLE users;--")
    chat(real, alice, "yes")
    assert real.get("/api/appointments", headers=alice["headers"]).json()["appointments"][0]["reason"] == "x'); DROP TABLE users;--"
    assert db_rows(real, "users")                                    # the table is still there


def test_profile_name_can_be_reused_with_same(real, alice, places):
    first = start_booking(real, alice)
    assert 'Reply "same" to use Alice' in first["response"]
    assert "Step 2 of 5" in chat(real, alice, "same")["response"]


def test_emergency_words_during_the_form_still_get_the_emergency_reply(real, alice, places):
    start_booking(real, alice)
    data = chat(real, alice, "I have chest pain")
    assert data["urgency_tier"] == "emergency" and "112" in data["response"]


# ----------------------------------------------------------------------------
# Demo partner hospital (sandbox)
# ----------------------------------------------------------------------------

@pytest.fixture()
def demo_on(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_PARTNER_ENABLED", True)


def test_demo_hospital_is_labelled_and_confirms_instantly(real, alice, places, demo_on):
    places.places = make_places(3)
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert len(data["facilities"]) == 4
    demo = data["facilities"][-1]
    assert demo["partner_demo"] is True and "DEMO" in demo["name"] and "sandbox" in demo["name"]

    chosen = chat(real, alice, "4")
    assert "sandbox hospital" in chosen["response"]
    chat(real, alice, "yes")
    summary = fill_form(real, alice, when="tomorrow evening")
    done = chat(real, alice, "yes")
    assert done["appointment"]["status"] == "confirmed" and done["appointment"]["is_demo"] is True
    assert "CONFIRMED (demo hospital)" in done["response"] and "No real hospital was contacted" in done["response"]
    assert "5:30 PM" in done["response"]


def test_demo_hospital_is_offered_alone_when_live_search_is_down(real, alice, demo_on, monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)    # osm path; the autouse stub raises PlacesUnavailable
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert len(data["facilities"]) == 1 and data["facilities"][0]["partner_demo"] is True
    assert "won't guess" in data["response"] or "couldn't complete" in data["response"]
    assert "sandbox" in data["response"]


def test_demo_hospital_is_off_by_default_in_tests(real, alice, places):
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert not any(f["partner_demo"] for f in data["facilities"])


# ----------------------------------------------------------------------------
# Privacy: delete my data
# ----------------------------------------------------------------------------

def test_user_can_erase_all_their_data_and_even_the_account(real, alice, bob, places):
    start_booking(real, alice)
    fill_form(real, alice)
    chat(real, alice, "yes")
    start_booking(real, bob)

    erased = real.delete("/api/me/data", headers=alice["headers"]).json()
    assert erased["counts"]["appointments"] == 1
    assert real.get("/api/appointments", headers=alice["headers"]).json()["appointments"] == []
    assert len(db_rows(real)) == 0 or all(r["user_id"] != str(alice["id"]) for r in db_rows(real))
    assert real.get("/api/conversations/history", headers=alice["headers"]).json()["history"] == []

    # Bob is untouched
    assert real.get("/api/appointments", headers=bob["headers"]).status_code == 200

    gone = real.delete("/api/me/data?delete_account=true", headers=alice["headers"]).json()
    assert gone["account_deleted"] is True
    login = real.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert login.status_code == 401
    assert real.delete("/api/me/data").status_code in (401, 403)


# ----------------------------------------------------------------------------
# Security controls
# ----------------------------------------------------------------------------

def test_login_is_rate_limited_per_account_and_address(client, alice):
    for _ in range(8):
        assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}).status_code == 401
    blocked = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert blocked.status_code == 429                                  # even the right password waits
    assert "Too many" in blocked.json()["detail"]


def test_unknown_email_and_wrong_password_look_identical(client, alice):
    a = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    b = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "whatever123"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_sign_ups_are_rate_limited(client):
    codes = []
    for i in range(12):
        codes.append(client.post("/api/auth/register", json={"name": f"U{i}x", "email": f"u{i}@example.com", "password": "password123"}).status_code)
    assert codes[:10] == [201] * 10 and codes[10] == 429


def test_security_headers_and_no_caching_of_api_responses(client, alice):
    r = client.get("/api/health-records", headers=alice["headers"])
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Request-ID"]


def test_emergency_messages_have_their_own_higher_limit(client, alice):
    for _ in range(31):                                                   # more than the normal 30/min
        assert client.post("/api/chat", json={"message": "I have chest pain"}, headers=alice["headers"]).status_code == 200
    normal = [client.post("/api/chat", json={"message": "hello there"}, headers=alice["headers"]).status_code for _ in range(32)]
    assert 429 in normal


def test_encryption_round_trip_and_wrong_key(monkeypatch):
    from app.core import crypto
    token = crypto.encrypt("Riya Sharma")
    assert token.startswith("enc1:") and "Riya" not in token
    assert crypto.decrypt(token) == "Riya Sharma"
    assert crypto.decrypt("plain text") == "plain text"
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", "a-different-key")
    assert "unreadable" in crypto.decrypt(token)


def test_cors_only_allows_the_configured_origins(client):
    ok = client.options("/api/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    bad = client.options("/api/chat", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
