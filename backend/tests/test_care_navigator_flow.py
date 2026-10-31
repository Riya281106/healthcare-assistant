"""
Flow tests for the care navigator, written from a real chat transcript:

  1. "book appointment for eye checkup near mumbai andheri east 400093"
       -> used to show the OLD saved list instead of searching the new area
  2. "suggest only those hospital where i can book online appointment"
       -> used to show the same 5 hospitals again, unfiltered
  3. "2" then "3"
       -> "2" worked, but "3" fell through to the AI, which invented "XYZ Hospital"

No network, no database: the search, booking lookup and saved state are replaced.
"""

import pytest

from app.services.agents import care_navigator as cn

USER = "u1"


def make_facilities(online=(), total=5):
    out = []
    for i in range(1, total + 1):
        booking = (
            {"status": "found", "url": f"https://h{i}.example/book", "external_provider": False}
            if i in online else {"status": "no_website"}
        )
        out.append({
            "n": i, "name": f"OLD Hospital {i}", "address": f"Old Road {i}, Jogeshwari West 4001{i:02d}",
            "specialty": "Eye care", "phone": None, "website": None, "maps_url": None,
            "rating": None, "open_now": None, "source": "OpenStreetMap",
            "distance_km": float(i), "booking": booking,
        })
    return out


@pytest.fixture()
def env(monkeypatch):
    class Env:
        state = {}
        searches = []

    e = Env()
    e.state = {}
    e.searches = []

    monkeypatch.setattr(cn, "load_care_state", lambda uid: dict(e.state.get(uid, {})))
    monkeypatch.setattr(cn, "save_care_state", lambda uid, s: e.state.__setitem__(uid, dict(s)))
    monkeypatch.setattr(cn, "get_profile_location", lambda uid: {})
    monkeypatch.setattr(cn, "_choose_provider", lambda: "osm")

    def fake_osm(spec_key, pin, locality, emergency=False, limit=10):
        e.searches.append({"spec": spec_key, "pin": pin, "locality": locality})
        return [
            {"name": f"NEW Hospital {i}", "address": f"Andheri East {pin or ''}", "source": "OpenStreetMap",
             "place_id": f"p{i}", "distance_km": 0.5 * i}
            for i in range(1, 7)
        ]
    monkeypatch.setattr(cn, "osm_search", fake_osm)
    monkeypatch.setattr(cn, "_lookup_bookings", lambda facs: [f.__setitem__("booking", {"status": "no_website"}) for f in facs])

    def seed(facilities, stage="results", **extra):
        e.state[USER] = {"stage": stage, "specialty": "eye", "pin": "400102",
                         "locality": "Jogeshwari West", "facilities": facilities, **extra}
    e.seed = seed
    return e


# ---------- 1. a new area must trigger a new search ----------

def test_booking_request_with_a_new_area_searches_again(env):
    env.seed(make_facilities())
    result = cn.handle("book appointment for eye checkup near mumbai andheri east 400093", USER)

    assert len(env.searches) == 1
    assert env.searches[0]["pin"] == "400093"
    assert "andheri" in env.searches[0]["locality"].lower()
    assert result["ui"] == "facility_results"
    assert all(f["name"].startswith("NEW") for f in result["facilities"])
    assert env.state[USER]["pin"] == "400093"


def test_booking_request_with_an_area_but_no_saved_list_searches(env):
    result = cn.handle("book appointment for eye checkup near andheri east 400093", USER)
    assert len(env.searches) == 1
    assert result["ui"] == "facility_results"


def test_find_hospital_in_a_new_area_searches_again(env):
    env.seed(make_facilities())
    cn.handle("find eye hospital near Powai 400076", USER)
    assert env.searches and env.searches[0]["pin"] == "400076"


def test_near_and_suggest_count_as_search_words(env):
    cn.handle("eye hospital near Andheri East 400093", USER)
    cn.handle("suggest eye hospital in Andheri East 400093", USER)
    assert len(env.searches) == 2


# ---------- 2. "only online booking" filters, never repeats the list unfiltered ----------

def test_online_only_keeps_just_verified_hospitals(env):
    env.seed(make_facilities(online=(3,)))
    result = cn.handle("suggest only those hospital where i can book online appointment", USER)

    assert env.searches == []
    assert [f["n"] for f in result["facilities"]] == [3]
    assert len(env.state[USER]["facilities"]) == 5       # saved list untouched, numbers still valid


def test_online_only_when_none_verified_says_so_honestly(env):
    env.seed(make_facilities(online=()))
    result = cn.handle("only those where i can book online", USER)

    assert env.searches == []
    assert "None of the 5" in result["response"]
    assert len(result["facilities"]) == 5


def test_number_after_online_only_filter_still_picks_the_right_hospital(env):
    env.seed(make_facilities(online=(3,)))
    cn.handle("show only hospitals with online booking", USER)
    result = cn.handle("3", USER)
    assert result["ui"] == "booking_link"
    assert result["facilities"][0]["n"] == 3
    assert result["booking_verified"] is True


# ---------- 3. numbers must keep working after a booking reply (no AI invention) ----------

def test_second_number_after_a_booking_reply_is_still_handled(env):
    env.seed(make_facilities(online=(3,)))

    first = cn.handle("2", USER)
    assert first["ui"] == "booking_link"
    assert first["facilities"][0]["n"] == 2

    second = cn.handle("3", USER)
    assert second is not None, "a bare number must never fall through to the AI"
    assert second["ui"] == "booking_link"
    assert second["facilities"][0]["n"] == 3


def test_number_outside_the_list_gets_a_clear_reply(env):
    env.seed(make_facilities(total=3))
    result = cn.handle("5", USER)
    assert result is not None
    assert result["ui"] == "facility_results"


def test_bare_number_with_no_list_is_left_for_other_flows(env):
    assert cn.handle("3", USER) is None


# ---------- existing behaviour must not change ----------

def test_book_hospital_2_still_works(env):
    env.seed(make_facilities())
    result = cn.handle("book hospital 2", USER)
    assert result["ui"] == "booking_link"
    assert result["facilities"][0]["n"] == 2
    assert env.searches == []


def test_book_with_no_number_and_no_area_still_asks_which(env):
    env.seed(make_facilities())
    result = cn.handle("book appointment", USER)
    assert result["ui"] == "facility_results"
    assert env.searches == []


def test_book_with_nothing_saved_and_no_area_still_needs_results(env):
    result = cn.handle("book hospital 2", USER)
    assert result["ui"] == "notice"
    assert env.searches == []


def test_same_area_booking_request_reuses_the_saved_list(env):
    env.seed(make_facilities(), pin="400093", locality="andheri east")
    result = cn.handle("book appointment near andheri east 400093", USER)
    assert env.searches == []
    assert result["ui"] == "facility_results"


def test_a_time_or_pronoun_after_the_number_is_not_read_as_a_place(env):
    env.seed(make_facilities())
    result = cn.handle("book hospital 2 for me tomorrow", USER)
    assert env.searches == []
    assert result["ui"] == "booking_link"
    assert result["facilities"][0]["n"] == 2


def test_book_in_the_evening_with_no_list_does_not_start_a_search(env):
    result = cn.handle("book appointment in the evening", USER)
    assert env.searches == []
    assert result["ui"] == "notice"


# ---------- specialty must come from the CURRENT message ----------

def test_plain_hospital_request_does_not_inherit_the_saved_eye_specialty(env):
    env.seed(make_facilities())                      # saved search was for "eye"
    cn.handle("i want list of nearest hospital in andheri east mumbai 400093", USER)
    assert env.searches[0]["spec"] == "general"


def test_booking_search_with_no_facility_word_keeps_the_saved_specialty(env):
    env.seed(make_facilities())
    cn.handle("book appointment near powai 400076", USER)
    assert env.searches[0]["spec"] == "eye"
    assert env.searches[0]["pin"] == "400076"


def test_named_specialist_is_recognised_as_a_facility_search():
    assert cn.is_facility_search("so tell me nearest dermatologist in andheri east 400093 mumbai")
    assert cn.is_facility_search("best cardiologist near Dadar 400028")


def test_unsupported_specialist_never_shows_the_wrong_hospitals(env, monkeypatch):
    monkeypatch.setattr(cn, "detect_specialty", lambda text: None)   # pretend no search exists for it
    env.seed(make_facilities())                                      # saved eye list is still there
    result = cn.handle("so tell me nearest dermatologist in andheri east 400093 mumbai", USER)

    assert env.searches == []                                        # no eye hospitals shown as skin doctors
    assert result is not None and result["ui"] == "notice"
    assert result["facilities"] == []
    assert "dermatologist" in result["response"]
    assert "google.com/maps/search" in result["response"]
    assert "400093" in result["response"]


# ---------- the area you type must be read correctly ----------

def test_area_after_tell_me_nearest_is_found():
    loc = cn.extract_location("so tell me nearest dermatologist in kandivali east mumbai")
    assert loc["locality"] == "kandivali east mumbai"
    assert loc["pin"] is None


def test_known_area_does_not_trigger_a_where_are_you_question(env, monkeypatch):
    monkeypatch.setattr(cn, "detect_specialty",
                        lambda text: cn.SPECIALTIES["general"] if "dermatologist" in (text or "") else None)
    result = cn.handle("so tell me nearest dermatologist in kandivali east mumbai", USER)
    assert result["ui"] == "facility_results"
    assert env.searches[0]["locality"] == "kandivali east mumbai"


def test_existing_location_phrases_still_work():
    assert cn.extract_location("find eye hospital near Powai 400076") == {"pin": "400076", "locality": "Powai"}
    assert cn.extract_location("hospital in Dadar, Mumbai")["locality"] == "Dadar, Mumbai"


# ---------- "online booking OR contact number" ----------

def test_booking_or_contact_keeps_places_with_a_phone_or_website(env):
    facs = make_facilities(online=(3,))
    facs[1]["phone"] = "022 1234 5678"                       # place 2 has only a phone
    facs[3]["website"] = "https://clinic4.example"           # place 4 has only a website
    env.seed(facs)
    result = cn.handle("suggest me only those clinic or hospital who has there online booking sites or there contact number", USER)

    assert env.searches == []
    assert [f["n"] for f in result["facilities"]] == [2, 3, 4]


def test_booking_or_contact_with_nothing_listed_says_so_and_never_invents(env):
    env.seed(make_facilities(online=()))
    result = cn.handle("suggest me only those clinic or hospital who has there online booking sites or there contact number", USER)

    assert env.searches == []
    assert "None of the 5" in result["response"]
    assert "phone number" in result["response"]
    assert "won't guess" in result["response"]


def test_booking_only_wording_still_ignores_phone_numbers(env):
    facs = make_facilities(online=(3,))
    facs[1]["phone"] = "022 1234 5678"
    env.seed(facs)
    result = cn.handle("suggest only those hospital where i can book online appointment", USER)
    assert [f["n"] for f in result["facilities"]] == [3]


def test_booked_claim_never_confirms(env):
    env.seed(make_facilities())
    result = cn.handle("I booked it", USER)
    assert result["facilities"] == []
    assert result["ui"] == "text"


# ---------- the hand-verified directory inside the search flow ----------

DIRECTORY = (
    "name,specialty,address,pin,locality,phone,website,booking_url,verified_on\n"
    'Verified Skin Clinic,dermatology;skin,"Shop 2, Road",400101,Kandivali East,022 1111 2222,https://skin.example,https://skin.example/book,2026-10-29\n'
    "Verified Eye Centre,eye,Road 5,400101,Kandivali East,022 3333 4444,https://eye.example,,2026-10-29\n"
)


@pytest.fixture()
def directory(tmp_path, monkeypatch):
    from app.services.integrations import local_directory
    path = tmp_path / "local.csv"
    path.write_text(DIRECTORY, encoding="utf-8")
    monkeypatch.setenv("LOCAL_FACILITIES_FILE", str(path))
    local_directory._CACHE.clear()
    return path


def test_verified_clinics_come_first_with_their_phone_and_website(env, directory):
    result = cn.handle("find eye hospital near kandivali east 400101", USER)
    first = result["facilities"][0]
    assert first["name"] == "Verified Eye Centre"
    assert first["phone"] == "022 3333 4444"
    assert first["website"] == "https://eye.example"
    assert "Verified local directory" in first["source"]
    assert any(f["name"].startswith("NEW") for f in result["facilities"][1:])    # map results still follow


def test_a_verified_booking_page_counts_as_online_booking(env, directory, monkeypatch):
    booker = cn.local_directory._to_place({
        "name": "Booker", "specialty": "eye", "pin": "400101", "locality": "Kandivali East", "address": "A",
        "phone": "022 1", "website": "", "booking_url": "https://booker.example/book", "verified_on": "",
    })
    monkeypatch.setattr(cn.local_directory, "search", lambda terms, pin, locality, limit=10, path=None: [booker])

    cn.handle("find eye hospital near kandivali east 400101", USER)
    result = cn.handle("suggest only those hospital where i can book online appointment", USER)

    assert [f["name"] for f in result["facilities"]] == ["Booker"]
    assert result["facilities"][0]["booking"]["url"] == "https://booker.example/book"


def test_verified_clinics_still_show_when_the_map_lookup_fails(env, directory, monkeypatch):
    def boom(*args, **kwargs):
        raise cn.LocationNotFound()
    monkeypatch.setattr(cn, "osm_search", boom)
    result = cn.handle("find eye hospital near kandivali east 400101", USER)
    assert result["ui"] == "facility_results"
    assert [f["name"] for f in result["facilities"]] == ["Verified Eye Centre"]


def test_unsupported_specialist_is_answered_from_the_directory(env, directory, monkeypatch):
    monkeypatch.setattr(cn, "detect_specialty", lambda text: None)       # no built-in dermatology search
    result = cn.handle("so tell me nearest dermatologist in kandivali east 400101", USER)

    assert env.searches == []                                            # map search not used for this
    assert result["ui"] == "facility_results"
    assert [f["name"] for f in result["facilities"]] == ["Verified Skin Clinic"]
    assert result["facilities"][0]["specialty"] == "Dermatology"
    assert result["facilities"][0]["booking"]["url"] == "https://skin.example/book"


def test_unsupported_specialist_with_nothing_in_the_directory_still_gets_the_honest_fallback(env, directory, monkeypatch):
    monkeypatch.setattr(cn, "detect_specialty", lambda text: None)
    result = cn.handle("nearest dermatologist in powai 400076", USER)
    assert result["ui"] == "notice"
    assert "google.com/maps/search" in result["response"]


def test_same_clinic_in_both_sources_is_listed_once_with_the_verified_details(env, directory, monkeypatch):
    def osm_with_duplicate(spec_key, pin, locality, emergency=False, limit=10):
        return [{"name": "Verified Eye Centre", "address": "Road 5 400101", "source": "OpenStreetMap", "place_id": "osm1"},
                {"name": "Other Eye Hospital", "address": "Road 9 400101", "source": "OpenStreetMap", "place_id": "osm2"}]
    monkeypatch.setattr(cn, "osm_search", osm_with_duplicate)
    names = [f["name"] for f in cn.handle("find eye hospital near kandivali east 400101", USER)["facilities"]]
    assert names == ["Verified Eye Centre", "Other Eye Hospital"]


def test_empty_directory_changes_nothing(env, tmp_path, monkeypatch):
    from app.services.integrations import local_directory
    empty = tmp_path / "empty.csv"
    empty.write_text("name,specialty,address,pin,locality,phone,website,booking_url,verified_on\n", encoding="utf-8")
    monkeypatch.setenv("LOCAL_FACILITIES_FILE", str(empty))
    local_directory._CACHE.clear()
    result = cn.handle("find eye hospital near kandivali east 400101", USER)
    assert all(f["name"].startswith("NEW") for f in result["facilities"])
