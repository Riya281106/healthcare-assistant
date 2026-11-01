"""The shipped hospital directory (app/data/local_facilities.csv): Maharashtra only, honestly labelled."""

from app.services.facilities.maharashtra import is_maharashtra_pin
from app.services.integrations import local_directory as ld


def rows():
    return ld._load(ld.DEFAULT_PATH)


def test_directory_loads_every_row_and_is_maharashtra_only():
    data = rows()
    assert len(data) >= 50
    assert all((not r["pin"]) or is_maharashtra_pin(r["pin"]) for r in data)
    assert not any("bhopal" in r["name"].lower() for r in data)


def test_rows_copied_from_a_third_party_list_are_never_called_verified():
    for r in rows():
        place = ld._to_place(r)
        assert "Verified" not in place["source"]
        assert "not checked with the hospital" in place["source"]


def test_search_by_pin_and_by_area():
    by_pin = ld.search(["general", "general hospital"], "400093", None)
    assert [p["name"] for p in by_pin] == ["Holy Spirit Hospital, Andheri"]
    by_area = ld.search(["eye", "ophthalmology / eye care"], None, "Santacruz")
    assert [p["name"] for p in by_area] == ["Kenia Eye Hospital, Santacruz"]
    assert ld.search(["eye", "ophthalmology / eye care"], "400093", None) == []     # no made-up fallback


def test_a_checked_row_still_shows_the_verified_label(tmp_path):
    path = tmp_path / "d.csv"
    path.write_text("name,specialty,address,pin,locality,phone,website,booking_url,verified_on,source_note\n"
                    "My Clinic,eye,1 Road,400001,Fort,022 1111 1111,,,2026-11-01,\n")
    place = ld.search(["eye"], "400001", None, path=str(path))[0]
    assert place["source"] == "Verified local directory (checked 2026-11-01)"
