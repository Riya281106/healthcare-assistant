"""
LOCAL VERIFIED DIRECTORY -- a free, hand-maintained list of clinics and hospitals.

Why this exists: free map data (OpenStreetMap) is missing many Indian clinics and almost
all of their phone numbers and websites. Paid listing APIs fill that gap; this file is the
free alternative. YOU add a clinic only after checking its details yourself (call it, or
read its own website). The app shows exactly what you wrote and never adds anything.

File: backend/app/data/local_facilities.csv   (override with LOCAL_FACILITIES_FILE in .env)
Columns: name, specialty, address, pin, locality, phone, website, booking_url, verified_on
  specialty   one or more words separated by ; or ,   e.g.  dermatology;skin   or   eye   or   general
  pin         6-digit PIN code of the clinic
  locality    area name, e.g. Kandivali East
  booking_url the clinic's OWN online booking page (leave blank if none)
  verified_on date you checked it, e.g. 2026-10-29   (shown to the patient)
Lines starting with # are ignored. A row needs at least a name, a specialty and a pin or locality.
"""

import csv
import os
import re
import threading
from typing import Dict, List, Optional, Sequence
from urllib.parse import quote_plus

from app.core.logging_config import get_logger

logger = get_logger("local_directory")

SOURCE_LABEL = "Verified local directory"
DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "local_facilities.csv",
)

_PIN = re.compile(r"^[1-9]\d{5}$")
_PHONE = re.compile(r"^[0-9+()\-\s;,/]{5,40}$")
_CACHE: Dict[str, tuple] = {}
_LOCK = threading.Lock()


def _clean_url(value: str) -> Optional[str]:
    value = (value or "").strip()
    return value if re.match(r"^https?://\S+$", value, re.I) else None


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).strip()


def _load(path: str) -> List[dict]:
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []

    with _LOCK:
        cached = _CACHE.get(path)
        if cached and cached[0] == mtime:
            return cached[1]

    rows: List[dict] = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            lines = [ln for ln in handle if ln.strip() and not ln.lstrip().startswith("#")]
        for number, raw in enumerate(csv.DictReader(lines), start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k}
            if not row.get("name") or not row.get("specialty"):
                logger.warning("local directory row %d skipped: needs name and specialty", number)
                continue
            if not (row.get("pin") or row.get("locality")):
                logger.warning("local directory row %d skipped: needs a pin or locality", number)
                continue
            if row.get("pin") and not _PIN.match(row["pin"]):
                logger.warning("local directory row %d skipped: bad PIN", number)
                continue
            phone = row.get("phone", "")
            if phone and not _PHONE.match(phone):
                logger.warning("local directory row %d: phone ignored (unexpected characters)", number)
                phone = ""
            row["phone"] = phone
            row["website"] = _clean_url(row.get("website", "")) or ""
            row["booking_url"] = _clean_url(row.get("booking_url", "")) or ""
            rows.append(row)
    except (OSError, csv.Error, UnicodeDecodeError):
        logger.exception("could not read local directory")
        return []

    with _LOCK:
        _CACHE[path] = (mtime, rows)
    return rows


def _specialty_matches(specialty: str, terms: Sequence[str]) -> bool:
    tokens = [t.strip() for t in re.split(r"[;,/|]", (specialty or "").lower()) if t.strip()]
    for token in tokens:
        for term in terms:
            if token == term:
                return True
            if len(token) >= 3 and len(term) >= 3 and (token.startswith(term) or term.startswith(token)):
                return True
    return False


_DIRECTIONS = {"east", "west", "north", "south"}
_GENERIC_AREA_WORDS = _DIRECTIONS | {"mumbai", "thane", "navi", "city", "nagar", "road", "india", "maharashtra", "suburban", "district"}


def _area_match(wanted: str, have: str) -> bool:
    """
    "kandivali east mumbai" matches "Kandivali East" and "Kandivali"; it never matches "Kandivali West",
    and a bare direction or city word ("east", "mumbai") matches nothing.
    """
    a, b = set(_norm(wanted).split()), set(_norm(have).split())
    if not a or not b:
        return False
    if (a & _DIRECTIONS) and (b & _DIRECTIONS) and (a & _DIRECTIONS) != (b & _DIRECTIONS):
        return False
    sig_a, sig_b = a - _GENERIC_AREA_WORDS, b - _GENERIC_AREA_WORDS
    if not sig_a or not sig_b:
        return False
    return sig_a <= b or sig_b <= a


def _location_score(row: dict, pin: Optional[str], locality: Optional[str]) -> Optional[int]:
    if pin and row.get("pin") == pin:
        return 0
    if locality and row.get("locality") and _area_match(locality, row["locality"]):
        return 1
    return None


def _to_place(row: dict) -> dict:
    address = row.get("address") or ", ".join(p for p in (row.get("locality"), row.get("pin")) if p)
    query = quote_plus(f"{row['name']} {address}".strip())
    verified = row.get("verified_on")
    return {
        "name": row["name"],
        "address": address,
        "phone": row.get("phone") or None,
        "website": row.get("website") or None,
        "maps_url": "https://www.google.com/maps/search/?api=1&query=" + query,
        "rating": None,
        "open_now": None,
        "source": f"{SOURCE_LABEL} (checked {verified})" if verified else SOURCE_LABEL,
        "distance_km": None,
        "place_id": "local:" + _norm(row["name"]),
        "booking_url": row.get("booking_url") or None,
        "specialty_label": re.split(r"[;,/|]", row["specialty"])[0].strip().title(),
    }


def search(terms: Sequence[str], pin: Optional[str], locality: Optional[str],
           limit: int = 10, path: Optional[str] = None) -> List[dict]:
    """Verified entries whose specialty matches `terms` and whose PIN/area matches. Best match first."""
    wanted = [t.lower().strip() for t in terms if t and t.strip()]
    if not wanted or not (pin or locality):
        return []

    rows = _load(path or os.getenv("LOCAL_FACILITIES_FILE") or DEFAULT_PATH)
    scored = []
    for row in rows:
        if not _specialty_matches(row["specialty"], wanted):
            continue
        score = _location_score(row, pin, locality)
        if score is not None:
            scored.append((score, row["name"].lower(), row))

    scored.sort(key=lambda item: item[:2])
    return [_to_place(row) for _s, _n, row in scored[:limit]]
