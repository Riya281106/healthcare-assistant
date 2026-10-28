"""
CARE NAVIGATOR  --  hospital / clinic discovery + appointment assistance.

A small, controlled state machine (no LLM decides what to do here):

    (symptom + find request) -> ask ONE red-flag question
        yes/severe  -> urgent guidance first, then offer emergency-service hospitals
        no          -> ask for PIN / locality (unless already known)
    PIN / locality known -> live Google Places search -> up to 5 results
        each result: facts from the listing + a booking link ONLY if one was
        actually found on the facility's own website
    "book hospital 2"   -> the verified booking link, or phone/website fallback
    "I booked it"       -> never claims confirmation

Rules enforced in code, not in a prompt:
  * No live data -> no results. Failure and "nothing found" are different messages.
  * Never invents a name, address, phone, website, booking page or slot.
  * Redirecting to a page is never described as booking.
  * The emergency detector runs BEFORE this module (see orchestrator.py).

handle() returns a result dict, or None when the message is not for this module.
"""

import re
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import asdict
from typing import Dict, List, Optional

from app.core.logging_config import get_logger
from app.services.facilities.booking_finder import BookingInfo, find_booking_link
from app.services.facilities.specialty import (
    SPECIALTIES,
    detect_specialty,
    specialty_by_key,
)
import os

from app.services.integrations.google_places import (
    PlacesUnavailable,
    is_configured,
    search_places_checked,
)
from app.services.integrations.osm_places import (
    SOURCE_LABEL as OSM_SOURCE,
    LocationNotFound,
    search_facilities as osm_search,
)
from app.services.session_context import (
    PIN_RE,
    get_profile_location,
    load_care_state,
    save_care_state,
)
from app.utils.messages import tr, what_label

logger = get_logger("care_navigator")

MAX_RESULTS = 5
BOOKING_LOOKUP_BUDGET_SECONDS = 6

# ----------------------------------------------------------------------------
# Intent cues (English / Hinglish / Hindi / Marathi)
# ----------------------------------------------------------------------------

_FACILITY_NOUN = re.compile(
    r"\b(?:hospital|hospitals|clinic|clinics|doctor|doctors|specialist|dentist|eye hospital|"
    r"daktar|dakter|aspatal|hospitals?)\b|अस्पताल|हॉस्पिटल|रुग्णालय|क्लिनिक|दवाखाना|डॉक्टर|डाक्टर",
    re.I,
)
_SEARCH_CUE = re.compile(
    r"\b(?:find|search|show|look(?:ing)? for|locate|need|want|nearby|near me|nearest|close to me|"
    r"dhundo|dhoondo|dhundh|batao|bataiye|dikhao|chahiye|paas|pass|shodh|sanga|dakhva|pahije)\b|"
    r"ढूँढ|ढूंढ|खोज|चाहिए|पास|जवळ|शोधा|हवे|दिखाओ|बताओ|सांगा",
    re.I,
)
_BOOKED_CLAIM = re.compile(
    r"\b(?:i|ive|i have|i already|we)\s+(?:just\s+|already\s+)?booked\b|\bbooked (?:my |the |an )?appointment\b|"
    r"\bappointment (?:is |has been |got )?(?:booked|confirmed|done|fixed)\b|\bbook (?:kar|ho) (?:li|liya|diya|gay[ie]|gaya)\b|"
    r"\bappointment (?:book|confirm) ho (?:gay[ie]|gaya)\b|बुक (?:कर (?:लिया|ली)|हो गया|हो गई)|बुक केली|बुक केले|बुक झाली",
    re.I,
)
_BOOKING_REQUEST = re.compile(
    r"\b(?:book|booking|appointment|schedule|reserve)\b|बुक|अपॉइंटमेंट|अपॉईंटमेंट|अपाॅइंटमेंट|नियुक्ति",
    re.I,
)
_SYMPTOM_WORDS = re.compile(
    r"\b(?:pain|painful|hurt|hurts|hurting|ache|aching|swelling|swollen|red|redness|itch\w*|burning|"
    r"infection|infected|bleeding|problem|trouble|dard|dukh\w*|jalan|takleef|taklif|sujan)\b|"
    r"दर्द|दुख|जलन|तकलीफ़|तकलीफ|सूजन|वेदना|त्रास|सूज",
    re.I,
)

_ORDINALS = {
    1: r"first|1st|pehla|pehle|pahla|पहला|पहले|पहिला|पहिले",
    2: r"second|2nd|doosra|dusra|dusre|दूसरा|दूसरे|दुसरा|दुसरे",
    3: r"third|3rd|teesra|tisra|तीसरा|तिसरा",
    4: r"fourth|4th|chautha|chautha|चौथा|चौथे",
    5: r"fifth|5th|paanchwa|panchva|पाँचवा|पांचवा|पाचवा",
}
_ORDINAL_RE = {n: re.compile(rf"\b(?:{p})\b|(?:{p})", re.I) for n, p in _ORDINALS.items()}
_NUMBER_AFTER = re.compile(
    r"(?:hospital|clinic|option|number|no\.?|num|#|अस्पताल|रुग्णालय|क्लिनिक|नंबर|क्रमांक)\s*[:\-]?\s*([1-9])\b", re.I
)
_NUMBER_BEFORE = re.compile(r"\b([1-9])\s*(?:number|no\.?|wala|wali|nambar)?\s*(?:hospital|clinic|wala|wali)\b", re.I)
_BARE_NUMBER = re.compile(r"^\s*(?:option\s*)?#?([1-9])\s*[.)]?\s*$", re.I)

_YES = re.compile(r"^\s*(?:yes|yeah|yep|yup|y|haan|han|haa|ha|hanji|ji haan|हाँ|हां|हा|होय|हो|जी हाँ)\b", re.I)
_NO = re.compile(r"^\s*(?:no|nope|nah|n|nahi|nahin|nhi|na|नहीं|नही|नाही|ना)\b", re.I)
_POSITIVE_WORDS = re.compile(
    r"\b(?:sudden|suddenly|severe|severely|worst|unbearable|blurred|blurry|cant see|cannot see|"
    r"loss of vision|lost vision|breathing|breathless|chest|faint\w*|bleeding heavily|achanak|achaanak|bahut tez|"
    r"behosh|saans)\b|अचानक|बहुत तेज़|बहुत तेज|तेज|धुंधला|अंधुक|तीव्र|बेहोश|सांस|साँस|छाती|सीने",
    re.I,
)
_NEGATED_POSITIVE = re.compile(
    r"\b(?:not|no|nahi|nahin|nhi|never|without|mild|slight|little|halka|halki)\b.{0,15}\b(?:sudden|severe|blurred|blurry|tez|achanak)\b|"
    r"\b(?:sudden|severe|blurred|blurry)\b.{0,10}\b(?:no|not|nahi|nahin)\b|नहीं|नाही",
    re.I,
)

_STOP_LOCALITY = re.compile(
    r"\b(?:hospital|hospitals|clinic|clinics|doctor|doctors|eye|dental|dentist|specialist|please|plz|me|you|the|a|an|my|"
    r"nearby|near|help|find|search|book|appointment)\b",
    re.I,
)
_LOCALITY_AFTER_CUE = re.compile(
    r"(?:\bnear|\bin|\bat|\baround|\bnearby|\bclose to|\bmein|\bme|\bmadhe|\bpaas|के पास|में|मध्ये|जवळ)\s+"
    r"([A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F .,\-]{2,40})",
    re.I,
)


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def is_booked_claim(message: str) -> bool:
    return bool(_BOOKED_CLAIM.search(message or ""))


def is_booking_request(message: str) -> bool:
    return bool(_BOOKING_REQUEST.search(message or "")) and not is_booked_claim(message)


def is_facility_search(message: str) -> bool:
    text = message or ""
    return bool(_FACILITY_NOUN.search(text)) and bool(_SEARCH_CUE.search(text))


def has_symptom_words(message: str) -> bool:
    return bool(_SYMPTOM_WORDS.search(message or ""))


def extract_location(message: str, allow_bare: bool = False) -> Dict[str, Optional[str]]:
    """
    {"pin": "400001"|None, "locality": "Dadar, Mumbai"|None}.
    `allow_bare`: treat a short reply that is only a place name as the locality
    (used right after we asked "PIN code or area?").
    """
    text = (message or "").strip()
    pin_match = PIN_RE.search(text)
    pin = pin_match.group(1) if pin_match else None

    locality = None
    cue = _LOCALITY_AFTER_CUE.search(PIN_RE.sub("", text))
    if cue:
        candidate = re.split(r"[?.!]| and | please| plz", cue.group(1), flags=re.I)[0].strip(" ,.-")
        if candidate and not _STOP_LOCALITY.fullmatch(candidate.lower()) and len(candidate) >= 3:
            if not _FACILITY_NOUN.search(candidate) and not detect_specialty(candidate):
                locality = candidate

    if not locality and allow_bare:
        # "Dadar" or "andheri east mumbai 400093": a short reply that is only a place (plus PIN)
        bare = re.sub(r"[^\w\s,\-\u0900-\u097F]", " ", PIN_RE.sub(" ", text)).strip()
        words = bare.split()
        if 1 <= len(words) <= 5 and not _STOP_LOCALITY.search(bare) and not text.endswith("?"):
            locality = " ".join(words).strip(" ,")

    return {"pin": pin, "locality": locality}


def selected_index(message: str, facilities: List[dict]) -> Optional[int]:
    """1-based index the user picked, by number, ordinal or name; else None."""
    text = message or ""
    count = len(facilities)

    for pattern in (_NUMBER_AFTER, _NUMBER_BEFORE, _BARE_NUMBER):
        found = pattern.search(text)
        if found:
            return int(found.group(1))

    for n, pattern in _ORDINAL_RE.items():
        if pattern.search(text):
            return n

    lowered = text.lower()
    for index, fac in enumerate(facilities, start=1):
        name = (fac.get("name") or "").lower()
        words = [w for w in re.findall(r"[a-z0-9]+", name) if len(w) > 3 and w not in ("hospital", "clinic", "centre", "center", "eye", "care", "multispeciality", "super", "speciality")]
        if name and (name in lowered or (len(words) >= 2 and sum(w in lowered for w in words) >= 2)):
            return index
    return None if count else None


def parse_screen_answer(message: str) -> str:
    """'positive' (red flag), 'negative', or 'unclear'."""
    text = (message or "").strip()
    if _NO.match(text):
        return "negative"
    if _NEGATED_POSITIVE.search(text) and not _YES.match(text):
        return "negative"
    if _YES.match(text) or _POSITIVE_WORDS.search(text):
        return "positive"
    return "unclear"


def _reply(text: str, *, tier: str = "normal", facilities: Optional[list] = None, ui: Optional[str] = None, extra: Optional[dict] = None) -> dict:
    out = {
        "response": text,
        "urgency_tier": tier,
        "agent": "CARE_NAVIGATOR",
        "rag_used": False,
        "sources": [],
        "facilities": facilities or [],
        "ui": ui or "text",
    }
    if extra:
        out.update(extra)
    return out


# ----------------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------------

def _where_text(pin: Optional[str], locality: Optional[str]) -> str:
    if pin and locality:
        return f"{locality} ({pin})"
    return pin or locality or ""


def _build_query(spec, pin: Optional[str], locality: Optional[str], emergency: bool) -> str:
    term = "24 hour emergency hospital" if emergency else spec.search_term
    if pin and locality:
        place = f"{locality} {pin}"
    else:
        place = pin or locality or ""
    return f"{term} near {place}, India"


def _lookup_bookings(facilities: List[dict]) -> None:
    """Fill fac['booking'] by checking each official website, in parallel, with a time budget."""
    targets = [f for f in facilities if f.get("website")]
    for fac in facilities:
        fac["booking"] = asdict(BookingInfo(status="no_website")) if not fac.get("website") else None
    if not targets:
        return

    pool = ThreadPoolExecutor(max_workers=min(5, len(targets)))
    try:
        futures = {pool.submit(find_booking_link, f["website"]): f for f in targets}
        done, _pending = wait(futures, timeout=BOOKING_LOOKUP_BUDGET_SECONDS)
        for future, fac in futures.items():
            if future in done:
                try:
                    fac["booking"] = asdict(future.result())
                    continue
                except Exception:
                    logger.exception("booking lookup failed")
            fac["booking"] = asdict(BookingInfo(status="unreachable"))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _choose_provider() -> str:
    """
    "google" when PLACES_PROVIDER=google, or when it is unset/auto and a Google key exists;
    otherwise "osm" (free, no key). Set PLACES_PROVIDER=osm to force OpenStreetMap.
    """
    setting = (os.getenv("PLACES_PROVIDER") or "auto").strip().lower()
    if setting == "google":
        return "google"
    if setting == "osm":
        return "osm"
    return "google" if is_configured() else "osm"


def _facility_record(position: int, place: dict, spec) -> dict:
    return {
        "n": position,
        "name": place.get("name"),
        "address": place.get("address") or None,
        "specialty": spec.label,
        "phone": place.get("phone"),
        "website": place.get("website"),
        "maps_url": place.get("maps_url"),
        "rating": place.get("rating"),
        "open_now": place.get("open_now"),
        "source": place.get("source") or "Google Maps listing",
        "distance_km": place.get("distance_km"),
        "booking": None,
    }


def _format_results(facilities: List[dict], spec_key: str, where: str, lang: str, source: str = "Google Maps listings") -> str:
    what = what_label(spec_key, lang)
    n = len(facilities)
    count_phrase = {
        "en": f"are {n} result{'s' if n != 1 else ''}",
        "hinglish": f"{n} result",
        "hi": f"{n} नतीजे",
        "mr": f"{n} निकाल",
    }.get(lang, f"are {n} result{'s' if n != 1 else ''}")

    lines = [tr("results_intro", lang, what=what, where=where, count_phrase=count_phrase, source=source)]
    if n < MAX_RESULTS:
        lines.append(tr("results_fewer", lang, n=n))
    lines.append("")

    unlisted = tr("lbl_not_listed", lang)
    for fac in facilities:
        lines.append(f"{fac['n']}. {fac['name']}")
        lines.append(f"   {tr('lbl_specialty', lang)}: {fac['specialty']}")
        lines.append(f"   {tr('lbl_address', lang)}: {fac['address'] or unlisted}")
        if fac.get("phone"):
            lines.append(f"   {tr('lbl_phone', lang)}: {fac['phone']}")
        lines.append(f"   {tr('lbl_website', lang)}: {fac['website'] or unlisted}")
        booking = fac.get("booking") or {}
        if booking.get("status") == "found":
            lines.append(f"   {tr('lbl_booking', lang)}: {booking['url']}")
        else:
            lines.append(f"   {tr('lbl_booking', lang)}: {tr('lbl_booking_unverified', lang)}")
        lines.append("")

    lines.append(tr("results_next", lang))
    return "\n".join(lines)


def _run_search(user_id: str, state: dict, spec_key: str, pin, locality, lang: str, emergency: bool = False) -> dict:
    spec = specialty_by_key(spec_key) or SPECIALTIES["general"]
    where = _where_text(pin, locality)
    what = what_label(spec.key, lang)

    # The Maps suggestion must be an English query, not the translated label.
    maps_what = what_label(spec.key, "en")

    # Whatever happens next, the flow is no longer "waiting for a location":
    # remember what the user told us and reset the step.
    save_care_state(user_id, {"stage": "none", "specialty": spec.key, "pin": pin, "locality": locality, "facilities": []})

    provider = _choose_provider()

    try:
        if provider == "google":
            if not is_configured():
                logger.warning("PLACES_PROVIDER=google but GOOGLE_PLACES_API_KEY is not set")
                return _reply(tr("search_not_configured", lang, what=maps_what, where=where), ui="notice")
            raw = search_places_checked(
                _build_query(spec, pin, locality, emergency),
                place_type=spec.place_type,
                limit=10,
            )
        else:
            raw = osm_search(spec.key, pin, locality, emergency=emergency, limit=10)

    except LocationNotFound:
        save_care_state(user_id, {**state, "stage": "awaiting_location", "specialty": spec.key, "emergency": emergency, "facilities": []})
        return _reply(tr("ask_clarify_location", lang), ui="ask_location")

    except PlacesUnavailable as exc:
        logger.warning("facility search unavailable (%s): %s", provider, exc)
        return _reply(tr("search_unavailable", lang, what=maps_what, where=where), ui="notice")

    seen, cleaned = set(), []
    for place in raw:
        name = (place.get("name") or "").strip()
        key = place.get("place_id") or name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        cleaned.append(place)

    if pin:
        cleaned.sort(key=lambda p: 0 if pin in (p.get("address") or "") else 1)

    cleaned = cleaned[:MAX_RESULTS]

    if not cleaned:
        save_care_state(user_id, {**state, "stage": "none", "facilities": [], "specialty": spec.key, "pin": pin, "locality": locality})
        return _reply(tr("no_results", lang, what=what, where=where), ui="notice")

    facilities = [_facility_record(i, place, spec) for i, place in enumerate(cleaned, start=1)]
    _lookup_bookings(facilities)

    save_care_state(user_id, {
        "stage": "results",
        "specialty": spec.key,
        "pin": pin,
        "locality": locality,
        "facilities": facilities,
    })

    logger.info("care search: specialty=%s results=%d", spec.key, len(facilities))
    source = facilities[0]["source"]
    return _reply(_format_results(facilities, spec.key, where, lang, source), facilities=facilities, ui="facility_results")


# ----------------------------------------------------------------------------
# Booking assistance
# ----------------------------------------------------------------------------

def _booking_reply(fac: dict, lang: str) -> dict:
    name = fac["name"]
    booking = fac.get("booking") or {}

    # A cached "could not reach the site" deserves one retry now.
    if booking.get("status") in (None, "unreachable") and fac.get("website"):
        try:
            booking = asdict(find_booking_link(fac["website"]))
            fac["booking"] = booking
        except Exception:
            logger.exception("booking retry failed")

    if booking.get("status") == "found":
        if booking.get("external_provider"):
            head = tr("book_found_external", lang, name=name, url=booking["url"], host=booking.get("provider_host") or "")
        else:
            head = tr("book_found_own", lang, name=name, url=booking["url"])
        text = head + "\n\n" + tr("book_steps", lang)
        return _reply(text, facilities=[fac], ui="booking_link", extra={"booking_url": booking["url"], "booking_verified": True})

    if fac.get("phone"):
        fallback = tr("book_fallback_phone", lang, phone=fac["phone"])
    elif fac.get("website"):
        fallback = tr("book_fallback_site", lang, url=fac["website"])
    else:
        fallback = tr("book_fallback_none", lang)

    return _reply(tr("book_not_found", lang, name=name, fallback=fallback), facilities=[fac], ui="booking_link", extra={"booking_url": None, "booking_verified": False})


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------

def handle(message: str, user_id: str, lang: str = "en") -> Optional[dict]:
    """Return a reply dict if this message belongs to the care-navigation flow, else None."""
    if not user_id:
        return None

    text = (message or "").strip()
    state = load_care_state(user_id)
    stage = state.get("stage", "none")
    facilities = state.get("facilities") or []

    # 1. "I booked it" -- never claim confirmation.
    if is_booked_claim(text):
        return _reply(tr("booked_claim", lang))

    # 2. Waiting for the answer to the red-flag question.
    if stage == "screening":
        answer = parse_screen_answer(text)
        if answer == "unclear" and not state.get("reasked"):
            save_care_state(user_id, {**state, "reasked": True})
            return _reply(tr("screen_reask", lang))
        if answer == "positive":
            save_care_state(user_id, {**state, "stage": "awaiting_location", "emergency": True, "reasked": False})
            return _reply(tr("screen_positive", lang), tier="urgent", ui="urgent_guidance")
        # negative (or still unclear after one re-ask): continue with routine search
        state = {**state, "stage": "awaiting_location", "emergency": False, "reasked": False}
        save_care_state(user_id, state)
        stage = "awaiting_location"
        known = get_profile_location(user_id)
        loc = {"pin": known.get("pin"), "locality": known.get("locality")}
        if loc["pin"] or loc["locality"]:
            return _run_search(user_id, state, state.get("specialty") or "general", loc["pin"], loc["locality"], lang)
        spec = specialty_by_key(state.get("specialty")) or SPECIALTIES["general"]
        return _reply(tr("ask_location", lang, what=what_label(spec.key, lang)), ui="ask_location")

    # 3. Waiting for a location.
    if stage == "awaiting_location":
        other_intent = is_booking_request(text) or is_facility_search(text)
        loc = extract_location(text, allow_bare=not other_intent)
        if loc["pin"] or loc["locality"]:
            # A long sentence or a question without a PIN is not an answer to "which area?"
            long_or_question = text.endswith("?") or len(text.split()) > 7
            if loc["pin"] or not long_or_question:
                return _run_search(
                    user_id, state, state.get("specialty") or "general",
                    loc["pin"], loc["locality"], lang, emergency=bool(state.get("emergency")),
                )
        if not other_intent:
            if text.endswith("?") or len(text.split()) > 7:
                return None  # unrelated question: leave the state, answer normally
            return _reply(tr("ask_clarify_location", lang), ui="ask_location")
        # otherwise fall through: a booking request or a new search is handled below

    # 4. Booking request.
    if is_booking_request(text) and (facilities or not is_facility_search(text)):
        if not facilities:
            return _reply(tr("book_need_results", lang), ui="notice")
        idx = selected_index(text, facilities)
        if idx is None:
            return _reply(tr("book_which", lang), facilities=facilities, ui="facility_results")
        if not 1 <= idx <= len(facilities):
            return _reply(tr("book_bad_index", lang, n=len(facilities)), facilities=facilities, ui="facility_results")
        chosen = facilities[idx - 1]
        reply = _booking_reply(chosen, lang)
        facilities[idx - 1] = chosen
        save_care_state(user_id, {**state, "stage": "booking_link_sent", "facilities": facilities, "selected": idx})
        return reply

    # 5. A bare choice ("2") right after results were shown.
    if stage == "results" and facilities:
        idx = selected_index(text, facilities) if _BARE_NUMBER.match(text) else None
        if idx is not None:
            if not 1 <= idx <= len(facilities):
                return _reply(tr("book_bad_index", lang, n=len(facilities)), facilities=facilities, ui="facility_results")
            reply = _booking_reply(facilities[idx - 1], lang)
            save_care_state(user_id, {**state, "stage": "booking_link_sent", "facilities": facilities, "selected": idx})
            return reply

    # 6. New facility search.
    if is_facility_search(text):
        spec = detect_specialty(text) or specialty_by_key(state.get("specialty")) or SPECIALTIES["general"]
        loc = extract_location(text)
        saved = get_profile_location(user_id)
        pin = loc["pin"] or (None if loc["locality"] else saved.get("pin"))
        locality = loc["locality"] or (None if loc["pin"] else saved.get("locality"))

        # Symptom wording ("my eye hurts, find eye hospitals"): one red-flag question first.
        if has_symptom_words(text) and not state.get("screened"):
            save_care_state(user_id, {
                "stage": "screening", "specialty": spec.key, "screened": True,
                "pin": pin, "locality": locality, "facilities": [],
            })
            key = "screen_eye" if spec.key == "eye" else "screen_generic"
            return _reply(tr(key, lang), ui="screening")

        if not (pin or locality):
            save_care_state(user_id, {"stage": "awaiting_location", "specialty": spec.key, "facilities": []})
            return _reply(tr("ask_location", lang, what=what_label(spec.key, lang)), ui="ask_location")

        return _run_search(user_id, {}, spec.key, pin, locality, lang)

    return None
