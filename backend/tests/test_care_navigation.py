"""
Tests A-L from the project brief, plus unit tests for the new modules.

What these tests can and cannot prove (be honest in the viva):
  * The LLM and Google Places are STUBBED. They prove routing, safety rules,
    language handling, state handling, and "never invent / never claim booked"
    behaviour of OUR code.
  * They do NOT prove how a real Groq model words an answer, or that real
    Google Places data is complete. Those need a manual run with real keys.
"""

import types

import pytest

import app.services.agents.care_navigator as nav
from app.services.facilities import booking_finder
from app.services.integrations.google_places import PlacesUnavailable


# ----------------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Tests must never call OpenStreetMap / Google / hospital websites."""
    monkeypatch.delenv("PLACES_PROVIDER", raising=False)

    def offline(*args, **kwargs):
        raise PlacesUnavailable("network disabled in tests")

    monkeypatch.setattr(nav, "osm_search", offline)
    monkeypatch.setattr(nav, "find_booking_link", lambda website: booking_finder.BookingInfo(status="unreachable"))


@pytest.fixture()
def real(client, monkeypatch):
    """Use the REAL orchestrator behind the API."""
    import app.main as main
    from app.services.agents.orchestrator import orchestrate
    monkeypatch.setattr(main, "orchestrate", orchestrate)
    return client


class FakeLLM:
    """Stands in for the Groq client; records every prompt it receives."""

    def __init__(self, reply="stub answer"):
        self.reply = reply
        self.prompts = []
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.prompts.append(kwargs["messages"][0]["content"])
        message = types.SimpleNamespace(content=self.reply)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


@pytest.fixture()
def llm(monkeypatch):
    import app.services.llm.service as service
    fake = FakeLLM()
    monkeypatch.setattr(service, "client", fake)
    return fake


def stub_retrieval(monkeypatch, context, sources):
    """
    Replace retrieval in EVERY agent that uses it, so no test reads the real
    ChromaDB (which differs between machines).

    Agents are imported lazily by the orchestrator, so they must be imported
    HERE first; otherwise they would import the real function later.
    """
    import importlib
    import pkgutil

    import app.services.agents as agents_pkg

    def fake(query, top_k=3):
        return context, list(sources)

    for info in pkgutil.iter_modules(agents_pkg.__path__):
        try:
            module = importlib.import_module(f"app.services.agents.{info.name}")
        except Exception:
            continue
        if hasattr(module, "retrieve_medical_context"):
            monkeypatch.setattr(module, "retrieve_medical_context", fake)


def make_places(n, pin="400001"):
    return [
        {
            "name": f"Eye Care Hospital {i}",
            "address": f"{i} Main Road, Mumbai {pin}",
            "phone": f"+91 22 0000 000{i}",
            "website": f"https://hospital{i}.example.org",
            "maps_url": f"https://maps.example/{i}",
            "rating": 4.0,
            "open_now": True,
            "place_type": "hospital",
            "place_id": f"pid{i}",
        }
        for i in range(1, n + 1)
    ]


class PlacesStub:
    def __init__(self, places=None, error=None):
        self.places = places if places is not None else make_places(6)
        self.error = error
        self.queries = []

    def __call__(self, query, place_type="hospital", limit=6):
        self.queries.append(query)
        if self.error:
            raise self.error
        return list(self.places)


@pytest.fixture()
def places(monkeypatch):
    stub = PlacesStub()
    monkeypatch.setattr(nav, "is_configured", lambda: True)
    monkeypatch.setattr(nav, "search_places_checked", stub)
    # default: hospital 1 has an own-site booking link, hospital 2 has none
    def fake_find(website):
        if website == "https://hospital1.example.org":
            return booking_finder.BookingInfo(status="found", url="https://hospital1.example.org/appointments")
        if website == "https://hospital3.example.org":
            return booking_finder.BookingInfo(
                status="found", url="https://book.practo.example/h3", external_provider=True, provider_host="book.practo.example"
            )
        return booking_finder.BookingInfo(status="not_found")
    monkeypatch.setattr(nav, "find_booking_link", fake_find)
    return stub


def chat(client, user, message, language="auto"):
    r = client.post("/api/chat", json={"message": message, "language": language}, headers=user["headers"])
    assert r.status_code == 200, r.text
    return r.json()


# ----------------------------------------------------------------------------
# Test A / B : multilingual
# ----------------------------------------------------------------------------

def test_A_hinglish_eye_pain_is_understood_and_answered_in_hinglish(real, alice, llm):
    data = chat(real, alice, "Meri aankh mein dard ho raha hai.")
    assert data["language"] == "hinglish"
    assert data["urgency_tier"] != "emergency"          # eye *pain* is not an emergency by itself
    assert "Hinglish" in llm.prompts[-1]                # the model was told to answer in Hinglish
    assert "aankh" in llm.prompts[-1].lower()           # and received the user's own words


def test_B_switch_to_marathi_and_keep_it(real, alice, llm):
    chat(real, alice, "Meri aankh mein dard ho raha hai.")
    data = chat(real, alice, "Please explain in Marathi.")
    assert data["language"] == "mr"
    assert "Marathi" in llm.prompts[-1]
    assert "aankh" in llm.prompts[-1].lower()           # earlier context was passed along
    # a later plain-English message keeps the chosen language
    data = chat(real, alice, "ok and what should I do next")
    assert data["language"] == "mr"
    assert "Marathi" in llm.prompts[-1]


def test_B2_selector_overrides_detection(real, alice, llm):
    data = chat(real, alice, "What is a fever?", language="hi")
    assert data["language"] == "hi"
    assert "Hindi" in llm.prompts[-1]


# ----------------------------------------------------------------------------
# Test C / D / J : knowledge, uncertainty, concise plain text
# ----------------------------------------------------------------------------

def test_C_hypertension_uses_retrieved_passages_and_returns_sources(real, alice, llm, monkeypatch):
    sources = [{"title": "Understanding Hypertension", "category": "Conditions", "section": "Overview", "relevance_score": 0.8}]
    stub_retrieval(monkeypatch, "[1] Understanding Hypertension - Overview\nHigh blood pressure means ...", sources)
    data = chat(real, alice, "What is hypertension?")
    assert data["rag_used"] is True
    assert data["sources"] == sources                   # only sources that were really retrieved
    assert "High blood pressure means" in llm.prompts[-1]


def test_D_no_matching_knowledge_means_no_sources_and_no_invented_context(real, alice, llm, monkeypatch):
    stub_retrieval(monkeypatch, "", [])
    data = chat(real, alice, "What is the dose of drug XYZ for rare disease Q?")
    assert data["rag_used"] is False
    assert data["sources"] == []
    assert "MEDICAL KNOWLEDGE" not in llm.prompts[-1]   # nothing was presented to the model as evidence


def test_J_markdown_symbols_are_removed_from_answers(real, alice, llm, monkeypatch):
    stub_retrieval(monkeypatch, "", [])
    llm.reply = "## Fever\n**Fever** is a high temperature.\n* Rest\n* Drink water"
    data = chat(real, alice, "What is a fever?")
    assert "**" not in data["response"] and "##" not in data["response"]
    assert "• Rest" in data["response"]


# ----------------------------------------------------------------------------
# Test E : emergency
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("message,lang", [
    ("I suddenly lost vision in one eye.", "en"),
    ("mujhe achanak ek aankh se dikhna band ho gaya", "hinglish"),
    ("अचानक आँख से दिखना बंद हो गया", "hi"),
    ("माझ्या डोळ्याला अचानक दिसत नाही", "mr"),
])
def test_E_sudden_vision_loss_is_an_emergency_in_every_language(real, alice, places, llm, message, lang):
    data = chat(real, alice, message)
    assert data["urgency_tier"] == "emergency"
    assert data["intent"] == "EMERGENCY"
    assert data["language"] == lang
    assert "112" in data["response"]
    assert data["facilities"] == []                     # no routine hospital list
    assert places.queries == []                         # and no search was even run
    assert llm.prompts == []                            # no LLM involved in an emergency


def test_E2_emergency_text_for_eye_mentions_not_rubbing(real, alice):
    data = chat(real, alice, "I suddenly lost vision in one eye.")
    assert "rub" in data["response"].lower()


# ----------------------------------------------------------------------------
# Test F / G / I : discovery
# ----------------------------------------------------------------------------

def test_F_symptom_plus_find_asks_red_flag_question_first_then_location(real, alice, places):
    data = chat(real, alice, "I have eye pain. Find nearby eye hospitals.")
    assert data["ui"] == "screening"
    assert "sudden or severe" in data["response"]
    assert places.queries == []                         # nothing searched yet

    data = chat(real, alice, "No, it is mild")
    assert data["ui"] == "ask_location"
    assert "PIN" in data["response"]
    assert places.queries == []


def test_F2_red_flag_yes_gives_urgent_guidance_not_a_routine_list(real, alice, places):
    chat(real, alice, "I have eye pain. Find nearby eye hospitals.")
    data = chat(real, alice, "Yes, it started suddenly and I see blurred")
    assert data["urgency_tier"] == "urgent"
    assert "112" in data["response"]
    assert data["facilities"] == []
    assert places.queries == []


def test_G_pin_returns_at_most_five_real_results_with_links(real, alice, places):
    chat(real, alice, "I have eye pain. Find nearby eye hospitals.")
    chat(real, alice, "No")
    data = chat(real, alice, "400001")
    assert data["ui"] == "facility_results"
    assert "400001" in places.queries[-1]
    assert "eye" in places.queries[-1].lower()
    assert len(data["facilities"]) == 5                 # 6 returned by the stub, capped at 5
    names = [f["name"] for f in data["facilities"]]
    assert names == [f"Eye Care Hospital {i}" for i in range(1, 6)]   # nothing invented
    first = data["facilities"][0]
    assert first["booking"]["status"] == "found"
    assert "https://hospital1.example.org/appointments" in data["response"]
    assert "not verified" in data["response"]           # hospitals without a verified link say so


def test_G2_fewer_than_five_is_stated(real, alice, places):
    places.places = make_places(3)
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert len(data["facilities"]) == 3
    assert "fewer than five" in data["response"]


def test_G3_results_without_website_or_phone_are_labelled_not_listed(real, alice, places):
    places.places = [{"name": "Tiny Clinic", "address": "Somewhere", "phone": None, "website": None,
                      "maps_url": "https://maps.example/x", "rating": None, "open_now": None,
                      "place_type": "doctor", "place_id": "x"}]
    data = chat(real, alice, "Find eye clinics near 400001")
    assert "not listed" in data["response"]
    assert data["facilities"][0]["booking"]["status"] == "no_website"


def test_I_saved_location_is_reused(real, alice, places, llm):
    chat(real, alice, "I live in 400001.")
    assert places.queries == []                         # stating a PIN alone searches nothing
    data = chat(real, alice, "Find eye clinics near me.")
    assert data["ui"] == "facility_results"             # did not ask for the PIN again
    assert "400001" in places.queries[-1]


def test_I2_location_is_asked_when_unknown(real, alice, places):
    data = chat(real, alice, "Find eye clinics near me.")
    assert data["ui"] == "ask_location"


def test_I3_pin_without_residence_wording_is_not_saved(real, alice, places, llm):
    chat(real, alice, "my otp is 482913")
    data = chat(real, alice, "Find eye clinics near me.")
    assert data["ui"] == "ask_location"


# ----------------------------------------------------------------------------
# Test H / L : booking
# ----------------------------------------------------------------------------

def _shown_results(real, alice):
    chat(real, alice, "Find eye hospitals near 400001")


def test_H_verified_booking_link_for_hospital_1(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "I want to book an appointment at Hospital 1.")
    assert data["booking_verified"] is True
    assert data["booking_url"] == "https://hospital1.example.org/appointments"
    assert "https://hospital1.example.org/appointments" in data["response"]
    assert "not booked anything" in data["response"] or "have not booked" in data["response"]


def test_H2_unverified_booking_falls_back_to_phone_and_never_invents_a_link(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "Book an appointment at Hospital 2")
    assert data["booking_verified"] is False
    assert data["booking_url"] is None
    assert "couldn't verify" in data["response"]
    assert "+91 22 0000 0002" in data["response"]
    assert "appointment" in data["response"]
    assert "https://hospital2.example.org/appointments" not in data["response"]


def test_H3_external_provider_is_explained(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "book hospital 3")
    assert data["booking_url"] == "https://book.practo.example/h3"
    assert "outside provider" in data["response"]


def test_H4_booking_without_a_choice_asks_which_one(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "I want to book an appointment")
    assert "Which hospital or clinic" in data["response"]


def test_H5_booking_with_no_results_asks_for_details(real, alice, places):
    data = chat(real, alice, "I want to book an appointment at Hospital 2")
    assert "PIN code or area" in data["response"]
    assert data["facilities"] == []


def test_H6_out_of_range_choice(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "book hospital 9")
    assert "between 1 and 5" in data["response"]


def test_H7_bare_number_after_results_selects_that_hospital(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "2")
    assert data["ui"] == "booking_link"
    assert data["facilities"][0]["name"] == "Eye Care Hospital 2"


def test_H8_hindi_booking_flow(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "अस्पताल 1 में अपॉइंटमेंट बुक करो")
    assert data["language"] == "hi"
    assert data["booking_url"] == "https://hospital1.example.org/appointments"
    assert "कुछ बुक नहीं किया" in data["response"]


def test_L_user_claims_booked_is_never_confirmed(real, alice, places):
    _shown_results(real, alice)
    data = chat(real, alice, "I booked my appointment.")
    text = data["response"].lower()
    assert "can't see or confirm" in text
    assert "is confirmed" not in text and "has been confirmed" not in text
    assert data["facilities"] == []


# ----------------------------------------------------------------------------
# Test K : tool failure
# ----------------------------------------------------------------------------

def test_K_search_failure_shows_no_results_and_no_invented_hospitals(real, alice, places):
    places.error = PlacesUnavailable("timeout")
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert "couldn't complete" in data["response"]
    assert data["facilities"] == []
    assert "Eye Care Hospital" not in data["response"]


def test_K2_missing_api_key_is_reported_honestly(real, alice, monkeypatch):
    monkeypatch.setenv("PLACES_PROVIDER", "google")      # Google forced, but no key
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert "isn't set up" in data["response"]
    assert data["facilities"] == []


def test_K3_zero_results_is_different_from_failure(real, alice, places):
    places.places = []
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert "couldn't find" in data["response"]
    assert "couldn't complete" not in data["response"]


# ----------------------------------------------------------------------------
# State, isolation, data controls
# ----------------------------------------------------------------------------

def test_state_is_private_per_user(real, alice, bob, places):
    chat(real, alice, "Find eye hospitals near 400001")
    data = chat(real, bob, "I want to book an appointment at Hospital 1")
    assert data["facilities"] == []                     # Bob cannot book Alice's list


def test_user_can_view_and_delete_stored_navigation_data(real, alice, places, llm):
    chat(real, alice, "I live in 400001.")
    chat(real, alice, "Find eye hospitals near me")
    r = real.get("/api/care-navigation/state", headers=alice["headers"])
    stored = r.json()["stored"]
    assert stored["profile_location"]["data"]["pin"] == "400001"
    assert "care_nav" in stored
    assert real.delete("/api/care-navigation/state", headers=alice["headers"]).json() == {"deleted": True}
    assert real.get("/api/care-navigation/state", headers=alice["headers"]).json()["stored"] == {}


def test_state_endpoints_require_login(real):
    assert real.get("/api/care-navigation/state").status_code in (401, 403)
    assert real.delete("/api/care-navigation/state").status_code in (401, 403)


def test_unrelated_question_while_waiting_for_location_is_not_hijacked(real, alice, llm):
    chat(real, alice, "Find eye clinics near me")
    data = chat(real, alice, "What is a fever and why does it happen at night?")
    assert data["agent"] != "CARE_NAVIGATOR"


# ----------------------------------------------------------------------------
# Unit tests: language
# ----------------------------------------------------------------------------

def test_language_detection_and_switching():
    from app.utils.language import detect_language, detect_language_switch, resolve_language
    assert detect_language("What is hypertension?") == "en"
    assert detect_language("Meri aankh mein dard ho raha hai.") == "hinglish"
    assert detect_language("मेरी आंख में दर्द हो रहा है") == "hi"
    assert detect_language("माझ्या डोळ्यात दुखतंय आणि मला काळजी वाटते") == "mr"
    assert detect_language("ஒரு கண் வலிக்கிறது") == "ta"
    assert detect_language_switch("Please explain in Marathi.") == "mr"
    assert detect_language_switch("Hindi mein batao") == "hi"
    assert detect_language_switch("मराठीत सांगा") == "mr"
    assert detect_language_switch("Marathi food recipes") is None
    assert resolve_language("hello", None, "mr") == ("mr", None)
    assert resolve_language("Please explain in Marathi.", "hi", None) == ("mr", "mr")


# ----------------------------------------------------------------------------
# Unit tests: booking finder
# ----------------------------------------------------------------------------

HTML = """
<html><body>
<a href="/about">About us</a>
<a href="/careers">Careers and jobs</a>
<a href="/appointments/book">Book Appointment</a>
<a href="https://other.example/x">Book a doctor</a>
<a href="javascript:void(0)">Book now</a>
<a href="/login">Patient login</a>
</body></html>
"""


def test_booking_links_are_extracted_from_real_html_only():
    links = booking_finder.extract_booking_links(HTML, "https://h.example.org/")
    assert links[0] == "https://h.example.org/appointments/book"
    assert all("javascript" not in link and "careers" not in link and "login" not in link for link in links)
    assert booking_finder.extract_booking_links("<p>no links</p>", "https://h.example.org/") == []


def test_find_booking_link_statuses(monkeypatch):
    monkeypatch.setattr(booking_finder, "is_public_http_url", lambda url: True)
    monkeypatch.setattr(booking_finder, "_fetch", lambda url: ("https://h.example.org/", HTML))
    info = booking_finder.find_booking_link("https://h.example.org")
    assert info.status == "found" and info.url == "https://h.example.org/appointments/book"
    assert info.external_provider is False

    monkeypatch.setattr(booking_finder, "_fetch", lambda url: ("https://h.example.org/", "<a href='/about'>About</a>"))
    assert booking_finder.find_booking_link("https://h.example.org").status == "not_found"

    monkeypatch.setattr(booking_finder, "_fetch", lambda url: None)
    assert booking_finder.find_booking_link("https://h.example.org").status == "unreachable"

    assert booking_finder.find_booking_link(None).status == "no_website"


def test_ssrf_guard_blocks_private_and_non_http_targets():
    for url in ("http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/latest/meta-data",
                "http://10.0.0.5/", "http://192.168.1.1/", "ftp://example.com/", "file:///etc/passwd", "not a url"):
        assert booking_finder.is_public_http_url(url) is False, url


def test_external_booking_provider_is_flagged(monkeypatch):
    monkeypatch.setattr(booking_finder, "is_public_http_url", lambda url: True)
    html = '<a href="https://book.provider.example/h">Book Appointment</a>'
    monkeypatch.setattr(booking_finder, "_fetch", lambda url: ("https://h.example.org/", html))
    info = booking_finder.find_booking_link("https://h.example.org")
    assert info.external_provider is True and info.provider_host == "book.provider.example"


# ----------------------------------------------------------------------------
# Unit tests: places "checked" search + specialty + helpers
# ----------------------------------------------------------------------------

def test_places_checked_distinguishes_failure_from_no_results(monkeypatch):
    import app.services.integrations.google_places as gp

    monkeypatch.setattr(gp, "GOOGLE_PLACES_API_KEY", "")
    with pytest.raises(PlacesUnavailable):
        gp.search_places_checked("eye hospital near 400001")
    assert gp.search_medical_places("eye hospital near 400001") == []   # old wrapper still safe

    monkeypatch.setattr(gp, "GOOGLE_PLACES_API_KEY", "key")

    def fake_get(url, params=None, timeout=None):
        return types.SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"status": "ZERO_RESULTS", "results": []},
        )
    monkeypatch.setattr(gp.requests, "get", fake_get)
    assert gp.search_places_checked("x") == []

    def denied(url, params=None, timeout=None):
        return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"status": "REQUEST_DENIED"})
    monkeypatch.setattr(gp.requests, "get", denied)
    with pytest.raises(PlacesUnavailable):
        gp.search_places_checked("x")


def test_specialty_detection():
    from app.services.facilities.specialty import detect_specialty
    assert detect_specialty("Meri aankh mein dard").key == "eye"
    assert detect_specialty("दाँत में दर्द").key == "dental"
    assert detect_specialty("kaan mein dard").key == "ent"
    assert detect_specialty("find a hospital") is None


def test_location_and_selection_parsing():
    assert nav.extract_location("400001") == {"pin": "400001", "locality": None}
    assert nav.extract_location("eye hospitals near Dadar, Mumbai")["locality"] == "Dadar, Mumbai"
    assert nav.extract_location("Dadar", allow_bare=True)["locality"] == "Dadar"
    assert nav.extract_location("find eye hospitals") == {"pin": None, "locality": None}
    facs = [{"name": "Alpha Eye Hospital"}, {"name": "Beta Vision Centre"}]
    assert nav.selected_index("Book appointment at Hospital 2", facs) == 2
    assert nav.selected_index("the second one", facs) == 2
    assert nav.selected_index("दूसरा वाला", facs) == 2
    assert nav.selected_index("book Beta Vision Centre", facs) == 2
    assert nav.selected_index("book an appointment", facs) is None
    assert nav.parse_screen_answer("No, not severe") == "negative"
    assert nav.parse_screen_answer("haan achanak hua") == "positive"
    assert nav.parse_screen_answer("hmm") == "unclear"


def test_localized_messages_exist_for_all_core_languages():
    from app.utils.messages import M
    for key, variants in M.items():
        for lang in ("en", "hinglish", "hi", "mr"):
            assert lang in variants, f"{key} missing {lang}"


# ----------------------------------------------------------------------------
# Retrieval: cutoff and query translation
# ----------------------------------------------------------------------------

def _chunks(*distances):
    return [{"document": f"doc{i}", "distance": d, "chunk_id": f"c{i}",
             "metadata": {"title": f"T{i}", "source": "s", "category": "c", "section": "x"}}
            for i, d in enumerate(distances)]


def test_retrieval_cutoff_drops_weak_matches(monkeypatch):
    import app.services.rag.retriever as retriever
    monkeypatch.setattr(retriever, "search_documents", lambda q, top_k=3: _chunks(0.55, 0.92, 1.16, 1.5))
    monkeypatch.setattr(retriever, "RELEVANCE_DISTANCE_CUTOFF", 1.0)
    kept = retriever.retrieve("What is hypertension?")
    assert [round(c["distance"], 2) for c in kept] == [0.55, 0.92]   # 1.16 and 1.5 are dropped


def test_non_english_query_is_translated_before_search(monkeypatch):
    import app.services.rag.retriever as retriever
    import app.services.llm.client as client_module
    seen = {}
    monkeypatch.setattr(client_module, "generate", lambda messages, system_instruction: "what to do for fever")
    monkeypatch.setattr(retriever, "search_documents", lambda q, top_k=3: seen.setdefault("q", q) and _chunks(0.6))
    retriever.retrieve("bukhar mein kya karein")
    assert seen["q"] == "what to do for fever"


def test_english_query_is_not_translated(monkeypatch):
    import app.services.rag.retriever as retriever
    import app.services.llm.client as client_module
    def boom(*a, **k):
        raise AssertionError("translation must not run for English")
    monkeypatch.setattr(client_module, "generate", boom)
    assert retriever.to_english_for_search("What is hypertension?") == "What is hypertension?"


def test_translation_failure_falls_back_to_original_query(monkeypatch):
    import app.services.rag.retriever as retriever
    import app.services.llm.client as client_module
    def down(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr(client_module, "generate", down)
    assert retriever.to_english_for_search("सर्दी जुकाम में क्या करें") == "सर्दी जुकाम में क्या करें"


# ----------------------------------------------------------------------------
# Regression tests from the first live run (screenshots)
# ----------------------------------------------------------------------------

def test_failed_search_does_not_leave_flow_stuck_waiting_for_location(real, alice, monkeypatch):
    """Live bug: after 'search not set up', 'book hospital 2' fell through to the old agent."""
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    chat(real, alice, "I have eye pain. Find nearby eye hospitals.")
    chat(real, alice, "no")
    chat(real, alice, "400001")                       # search cannot run (no key)
    data = chat(real, alice, "I want to book an appointment at Hospital 2.")
    assert data["agent"] == "CARE_NAVIGATOR"          # not the old hospital agent
    assert "PIN code or area" in data["response"]


def test_booking_request_while_waiting_for_location_is_not_swallowed(real, alice, places):
    chat(real, alice, "Find eye clinics near me")     # now waiting for a location
    data = chat(real, alice, "I want to book an appointment at Hospital 2.")
    assert data["agent"] == "CARE_NAVIGATOR"
    assert "PIN code or area" in data["response"]


def test_place_name_with_pin_keeps_both(real, alice, places):
    chat(real, alice, "Find eye clinics near me")
    chat(real, alice, "andheri east mumbai 400093")
    assert "andheri east mumbai" in places.queries[-1].lower()
    assert "400093" in places.queries[-1]


def test_maps_suggestion_is_an_english_query_even_in_marathi(real, alice, monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    data = chat(real, alice, "Find eye hospitals near 400001", language="mr")
    assert "eye clinics and hospitals near 400001" in data["response"]


def test_language_choice_is_visible_and_can_be_reset(real, alice, llm):
    chat(real, alice, "Meri aankh mein dard ho raha hai.")
    data = chat(real, alice, "Please explain in Marathi.")
    assert data["language"] == "mr" and data["language_pinned"] is True
    data = chat(real, alice, "ok thanks")             # selector still "auto": preference stays
    assert data["language"] == "mr" and data["language_pinned"] is True
    data = chat(real, alice, "What is a fever?", language="reset")   # user picked Auto by hand
    assert data["language"] == "en" and data["language_pinned"] is False
    data = chat(real, alice, "ok thanks")
    assert data["language"] == "en"


# ----------------------------------------------------------------------------
# Free provider: OpenStreetMap (no key, no card)
# ----------------------------------------------------------------------------

import app.services.integrations.osm_places as osm


def osm_place(i, **over):
    base = {
        "name": f"OSM Eye Clinic {i}", "address": f"{i} Lane, Mumbai", "phone": None,
        "website": None, "maps_url": f"https://www.google.com/maps/search/?api=1&query=18.9,72.8{i}",
        "rating": None, "open_now": None, "place_type": "clinic", "place_id": f"node/{i}",
        "source": osm.SOURCE_LABEL, "distance_km": float(i),
    }
    base.update(over)
    return base


def test_default_provider_is_osm_when_no_google_key(monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    assert nav._choose_provider() == "osm"
    monkeypatch.setattr(nav, "is_configured", lambda: True)
    assert nav._choose_provider() == "google"
    monkeypatch.setenv("PLACES_PROVIDER", "osm")
    assert nav._choose_provider() == "osm"


def test_osm_results_are_shown_with_honest_source_and_missing_fields(real, alice, monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    monkeypatch.setattr(nav, "osm_search", lambda key, pin, loc, emergency=False, limit=10: [osm_place(i) for i in range(1, 7)])
    data = chat(real, alice, "Find eye hospitals near 400001")
    assert len(data["facilities"]) == 5
    assert "OpenStreetMap" in data["response"] and "may be incomplete" in data["response"]
    assert data["facilities"][0]["source"].startswith("OpenStreetMap")
    assert data["facilities"][0]["distance_km"] == 1.0
    assert "not listed" in data["response"]                  # website missing in the data


def test_osm_unknown_location_asks_again_instead_of_failing(real, alice, monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    def nowhere(*a, **k):
        raise osm.LocationNotFound("999999")
    monkeypatch.setattr(nav, "osm_search", nowhere)
    data = chat(real, alice, "Find eye hospitals near 999999")
    assert data["ui"] == "ask_location"
    data = chat(real, alice, "Dadar, Mumbai")                 # still waiting for a usable location
    assert data["agent"] == "CARE_NAVIGATOR"


def test_osm_outage_is_reported_not_faked(real, alice, monkeypatch):
    monkeypatch.setattr(nav, "is_configured", lambda: False)
    data = chat(real, alice, "Find eye hospitals near 400001")   # autouse stub raises PlacesUnavailable
    assert "couldn't complete" in data["response"]
    assert data["facilities"] == []


OVERPASS_SAMPLE = [
    {"type": "node", "id": 1, "lat": 18.9400, "lon": 72.8350,
     "tags": {"name": "Far Eye Hospital", "amenity": "hospital", "website": "farhospital.example.org",
              "phone": "+91 22 1111 1111", "addr:street": "MG Road", "addr:city": "Mumbai", "addr:postcode": "400001"}},
    {"type": "way", "id": 2, "center": {"lat": 18.9330, "lon": 72.8340},
     "tags": {"name": "Near Netralaya", "amenity": "clinic"}},
    {"type": "node", "id": 3, "lat": 18.9331, "lon": 72.8341, "tags": {"amenity": "clinic"}},                 # no name: dropped
    {"type": "node", "id": 4, "tags": {"name": "No Coordinates", "amenity": "clinic"}},                         # no coords: dropped
    {"type": "way", "id": 5, "center": {"lat": 18.9330, "lon": 72.8340}, "tags": {"name": "Near Netralaya", "amenity": "clinic"}},  # duplicate
    {"type": "node", "id": 6, "lat": 18.9500, "lon": 72.8400, "tags": {"name": "Bad Site", "amenity": "clinic", "website": "not a url"}},
]


def test_osm_parsing_sorts_by_distance_and_never_invents_fields():
    places = osm.parse_elements(OVERPASS_SAMPLE, 18.9322, 72.8353)
    assert [p["name"] for p in places] == ["Near Netralaya", "Far Eye Hospital", "Bad Site"]
    near, far, bad = places
    assert near["phone"] is None and near["website"] is None and near["address"] is None
    assert far["website"] == "https://farhospital.example.org"
    assert far["address"] == "MG Road, Mumbai, 400001"
    assert far["phone"] == "+91 22 1111 1111"
    assert bad["website"] is None                                  # invalid URL is not shown
    assert near["distance_km"] < far["distance_km"] < bad["distance_km"]
    assert all(p["source"] == osm.SOURCE_LABEL for p in places)


def test_osm_emergency_prefers_hospitals_with_emergency_tag():
    elements = [
        {"type": "node", "id": 1, "lat": 18.930, "lon": 72.830, "tags": {"name": "Close No-ER", "amenity": "hospital"}},
        {"type": "node", "id": 2, "lat": 18.960, "lon": 72.860, "tags": {"name": "Farther With ER", "amenity": "hospital", "emergency": "yes"}},
    ]
    assert osm.parse_elements(elements, 18.93, 72.83, emergency=True)[0]["name"] == "Farther With ER"
    assert osm.parse_elements(elements, 18.93, 72.83, emergency=False)[0]["name"] == "Close No-ER"


def test_overpass_query_matches_specialty():
    eye = osm.build_overpass_query("eye", 18.93, 72.83, 5000, emergency=False)
    assert "ophthalm" in eye and "netralaya" in eye and "around:5000" in eye and "out center" in eye
    assert 'amenity"="dentist' in osm.build_overpass_query("dental", 18.93, 72.83, 5000, False)
    assert 'amenity"="hospital' in osm.build_overpass_query("eye", 18.93, 72.83, 5000, emergency=True)


def test_osm_geocoding_and_errors(monkeypatch):
    osm._geocode_cached.cache_clear()
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(params)
        return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: [{"lat": "18.9322", "lon": "72.8353"}])
    monkeypatch.setattr(osm.requests, "get", fake_get)
    assert osm.geocode("400001", None) == (18.9322, 72.8353)
    assert calls[0]["postalcode"] == "400001" and calls[0]["country"] == "India"
    osm.geocode("400001", None)
    assert len(calls) == 1                                          # cached: polite to the public server

    osm._geocode_cached.cache_clear()
    monkeypatch.setattr(osm.requests, "get", lambda *a, **k: types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: []))
    with pytest.raises(osm.LocationNotFound):
        osm.geocode("999999", None)

    osm._geocode_cached.cache_clear()
    def boom(*a, **k):
        raise osm.requests.ConnectionError("down")
    monkeypatch.setattr(osm.requests, "get", boom)
    with pytest.raises(PlacesUnavailable):
        osm.geocode("400001", None)
    osm._geocode_cached.cache_clear()


def test_osm_search_widens_radius_once_and_falls_back_to_mirror(monkeypatch):
    monkeypatch.setattr(osm, "geocode", lambda pin, loc: (18.9322, 72.8353))
    radii = []

    def fake_overpass(query):
        radii.append(5000 if "around:5000" in query else 15000)
        return OVERPASS_SAMPLE[:1] if len(radii) == 1 else OVERPASS_SAMPLE
    monkeypatch.setattr(osm, "_run_overpass", fake_overpass)
    places = osm.search_facilities("eye", "400001", None)
    assert radii == [5000, 15000]                                  # too few at 5 km, so widened once
    assert len(places) == 3

    # mirror fallback inside _run_overpass
    urls = []
    def post(url, data=None, headers=None, timeout=None):
        urls.append(url)
        if len(urls) == 1:
            raise osm.requests.ConnectionError("down")
        return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"elements": [1]})
    monkeypatch.undo()
    monkeypatch.setattr(osm.requests, "post", post)
    assert osm._run_overpass("q") == [1] and len(urls) == 2


NOMINATIM_SAMPLE = [
    {"category": "amenity", "type": "hospital", "name": "Nominatim Eye Hospital", "lat": "18.9400", "lon": "72.8350",
     "osm_type": "node", "osm_id": 11,
     "extratags": {"phone": "+91 22 2222 2222", "website": "nominatimhospital.example.org"},
     "address": {"road": "Colaba Road", "city": "Mumbai", "postcode": "400005"}},
    {"category": "shop", "type": "optician", "name": "Not Healthcare Class", "lat": "18.94", "lon": "72.83"},
    {"category": "amenity", "type": "restaurant", "name": "Eye Restaurant", "lat": "18.94", "lon": "72.83"},
    {"category": "healthcare", "type": "clinic", "display_name": "Near Clinic, Mumbai", "lat": "18.9330", "lon": "72.8340",
     "osm_type": "way", "osm_id": 12},
]


def test_nominatim_results_parse_and_filter_non_health_places():
    places = osm.parse_nominatim_results(NOMINATIM_SAMPLE, 18.9322, 72.8353)
    assert [p["name"] for p in places] == ["Near Clinic", "Nominatim Eye Hospital"]
    far = places[1]
    assert far["website"] == "https://nominatimhospital.example.org"
    assert far["address"] == "Colaba Road, Mumbai, 400005"
    assert places[0]["phone"] is None and places[0]["address"] is None


def test_overpass_outage_falls_back_to_nominatim(monkeypatch):
    monkeypatch.setattr(osm, "geocode", lambda pin, loc: (18.9322, 72.8353))
    def down(query):
        raise PlacesUnavailable("overpass down")
    monkeypatch.setattr(osm, "_run_overpass", down)
    monkeypatch.setattr(osm.requests, "get",
                        lambda *a, **k: types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: NOMINATIM_SAMPLE))
    places = osm.search_facilities("eye", "400001", None)
    assert [p["name"] for p in places] == ["Near Clinic", "Nominatim Eye Hospital"]


def test_everything_down_is_reported_as_unavailable(monkeypatch):
    monkeypatch.setattr(osm, "geocode", lambda pin, loc: (18.9322, 72.8353))
    def down(*a, **k):
        raise PlacesUnavailable("down")
    monkeypatch.setattr(osm, "_run_overpass", down)
    def boom(*a, **k):
        raise osm.requests.ConnectionError("down")
    monkeypatch.setattr(osm.requests, "get", boom)
    with pytest.raises(PlacesUnavailable):
        osm.search_facilities("eye", "400001", None)
