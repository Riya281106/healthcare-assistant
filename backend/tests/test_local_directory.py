"""The hand-verified clinic directory: reading the CSV, matching, and refusing bad rows."""

import pytest

from app.services.integrations import local_directory as ld

HEADER = "name,specialty,address,pin,locality,phone,website,booking_url,verified_on\n"


@pytest.fixture()
def csv_file(tmp_path):
    def make(body: str):
        path = tmp_path / "clinics.csv"
        path.write_text(HEADER + body, encoding="utf-8")
        return str(path)
    return make


def test_matches_by_pin_and_specialty(csv_file):
    path = csv_file(
        'Skin Care Clinic,dermatology;skin,"Shop 1, Road",400101,Kandivali East,022 1111 2222,https://skin.example,https://skin.example/book,2026-10-29\n'
        'Eye Clinic,eye,Road 2,400101,Kandivali East,022 3333 4444,,,2026-10-29\n'
    )
    found = ld.search(["dermatolog"], "400101", None, path=path)
    assert [p["name"] for p in found] == ["Skin Care Clinic"]
    place = found[0]
    assert place["phone"] == "022 1111 2222"
    assert place["website"] == "https://skin.example"
    assert place["booking_url"] == "https://skin.example/book"
    assert "Verified local directory" in place["source"] and "2026-10-29" in place["source"]
    assert place["specialty_label"] == "Dermatology"
    assert place["maps_url"].startswith("https://www.google.com/maps/search/")


def test_matches_by_area_name_when_no_pin(csv_file):
    path = csv_file("Skin Care Clinic,dermatology,Road,400101,Kandivali East,022 1111 2222,,,\n")
    assert ld.search(["dermatolog"], None, "kandivali east mumbai", path=path)
    assert ld.search(["dermatolog"], None, "Kandivali", path=path)              # "Kandivali" means this one too
    assert ld.search(["dermatolog"], None, "Kandivali West", path=path) == []   # the other side of the railway is not it
    assert ld.search(["dermatolog"], None, "east", path=path) == []             # a bare direction matches nothing
    assert ld.search(["dermatolog"], None, "Mumbai", path=path) == []           # nor does a bare city name


def test_pin_match_ranks_before_area_match(csv_file):
    path = csv_file(
        "Area Only,eye,Road,400099,Kandivali East,,,,\n"
        "Exact Pin,eye,Road,400101,Borivali,,,,\n"
    )
    names = [p["name"] for p in ld.search(["eye"], "400101", "kandivali east", path=path)]
    assert names == ["Exact Pin", "Area Only"]


def test_other_area_and_other_specialty_do_not_match(csv_file):
    path = csv_file("Skin Care Clinic,dermatology,Road,400101,Kandivali East,022 1111 2222,,,\n")
    assert ld.search(["dermatolog"], "400093", "Andheri East", path=path) == []
    assert ld.search(["dental"], "400101", None, path=path) == []


def test_no_location_means_no_results(csv_file):
    path = csv_file("Skin Care Clinic,dermatology,Road,400101,Kandivali East,022 1111 2222,,,\n")
    assert ld.search(["dermatolog"], None, None, path=path) == []


def test_bad_rows_are_skipped_not_trusted(csv_file):
    path = csv_file(
        ",eye,Road,400101,Area,,,,\n"                                   # no name
        "No Specialty,,Road,400101,Area,,,,\n"                          # no specialty
        "No Place,eye,Road,,,,,,\n"                                     # no pin and no area
        "Bad Pin,eye,Road,12345,Area,,,,\n"                             # PIN not 6 digits
        "Good,eye,Road,400101,Area,<script>x</script>,javascript:alert(1),ftp://x,\n"
    )
    found = ld.search(["eye"], "400101", None, path=path)
    assert [p["name"] for p in found] == ["Good"]
    assert found[0]["phone"] is None                  # odd characters dropped, not displayed
    assert found[0]["website"] is None                # only http/https links are kept
    assert found[0]["booking_url"] is None


def test_comment_lines_and_missing_file_are_safe(tmp_path, csv_file):
    path = csv_file("# a comment line\nReal,eye,Road,400101,Area,022 1111 2222,,,\n")
    assert [p["name"] for p in ld.search(["eye"], "400101", None, path=path)] == ["Real"]
    assert ld.search(["eye"], "400101", None, path=str(tmp_path / "nope.csv")) == []


def test_edits_to_the_file_are_picked_up(csv_file, tmp_path):
    import os, time
    path = csv_file("One,eye,Road,400101,Area,,,,\n")
    assert len(ld.search(["eye"], "400101", None, path=path)) == 1
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("Two,eye,Road,400101,Area,,,,\n")
    os.utime(path, (time.time() + 5, time.time() + 5))
    assert len(ld.search(["eye"], "400101", None, path=path)) == 2
