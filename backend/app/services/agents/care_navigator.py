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

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.agents import appointment_flow
from app.services.facilities.booking_finder import BookingInfo, find_booking_link
from app.services.facilities.links import directions_url, phone_lookup_url
from app.services.facilities.maharashtra import is_maharashtra_pin
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
from app.services.integrations import local_directory
from app.services.integrations.osm_places import (
    SOURCE_LABEL as OSM_SOURCE,
    LocationNotFound,
    OutsideMaharashtra,
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

MAX_RESULTS = 10
BOOKING_LOOKUP_BUDGET_SECONDS = 6

# ----------------------------------------------------------------------------
# Intent cues (English / Hinglish / Hindi / Marathi)
# ----------------------------------------------------------------------------

_FACILITY_NOUN = re.compile(
    r"\b(?:hospital|hospitals|clinic|clinics|doctor|doctors|specialist|dentist|eye hospital|"
    r"daktar|dakter|aspatal|hospitals?|"
    r"dermatologists?|skin doctor|skin specialist|trichologist|cardiologists?|orthop[a]?edic|gyn[a]?ecologists?|"
    r"p[a]?ediatricians?|neurologists?|psychiatrists?|urologists?|ent|physicians?|diabetologists?|endocrinologists?|"
    r"oncologists?|nephrologists?|gastroenterologists?|pulmonologists?|ophthalmologists?|optometrists?)\b|अस्पताल|हॉस्पिटल|रुग्णालय|क्लिनिक|दवाखाना|डॉक्टर|डाक्टर",
    re.I,
)
_SEARCH_CUE = re.compile(
    r"\b(?:find|search|show|look(?:ing)? for|locate|need|want|nearby|near|near me|nearest|close to me|"
    r"suggest|recommend|best|"
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


# Plain "hospital / clinic / doctor" with no specialty means ANY of them -- it must not
# inherit the specialty of an earlier search ("eye") that is still saved.
_GENERIC_FACILITY = re.compile(r"\b(?:hospitals?|clinics?|doctors?)\b", re.I)
# A named kind of doctor. If we have no search for it, say so instead of showing wrong places.
_SPECIALIST_NOUN = re.compile(
    r"\b(?:dermatologists?|skin doctor|skin specialist|trichologist|cardiologists?|orthop[a]?edic|gyn[a]?ecologists?|"
    r"p[a]?ediatricians?|neurologists?|psychiatrists?|urologists?|ent|physicians?|diabetologists?|endocrinologists?|"
    r"oncologists?|nephrologists?|gastroenterologists?|pulmonologists?|ophthalmologists?|optometrists?)\b",
    re.I,
)

# "suggest only those hospitals where I can book online"
_ONLINE_ONLY = re.compile(
    r"\b(?:only|just|sirf|keval|fakt)\b.{0,60}\b(?:online|website|web site|contact|phone)\b|"
    r"\b(?:online|website|web site)\b.{0,40}\b(?:only|just|sirf|keval|fakt)\b|"
    r"\bwith online (?:booking|appointments?)\b",
    re.I,
)

# "...online booking sites OR contact number": a phone number or website is also acceptable.
_CONTACT_OK = re.compile(r"\b(?:contact|phone|number|mobile|call|website|web site|sites?)\b", re.I)

# Texts for the "online booking only" reply (kept here so messages.py is untouched).
_EXTRA_TEXT = {
    "online_only_intro": {
        "en": "Only {found} of your {total} results has an online booking page I could verify. The numbers match your list:",
        "hinglish": "Aapke {total} results mein se sirf {found} ka online booking page verify ho paya. Numbers aapki list jaise hi hain:",
        "hi": "आपके {total} नतीजों में से सिर्फ़ {found} का ऑनलाइन बुकिंग पेज मैं जाँच पाया। नंबर आपकी सूची के अनुसार ही हैं:",
        "mr": "तुमच्या {total} निकालांपैकी फक्त {found} चे ऑनलाइन बुकिंग पेज मी तपासू शकलो. क्रमांक तुमच्या यादीप्रमाणेच आहेत:",
    },
    "online_only_none": {
        "en": "None of the {total} places in your list has an online booking page that I could verify. Here is how to reach each one:",
        "hinglish": "Aapki list ke {total} jagah mein se kisi ka bhi online booking page verify nahi ho paya. Sampark ka tarika:",
        "hi": "आपकी सूची की {total} जगहों में से किसी का भी ऑनलाइन बुकिंग पेज मैं जाँच नहीं पाया। संपर्क का तरीका:",
        "mr": "तुमच्या यादीतील {total} ठिकाणांपैकी कोणाचेही ऑनलाइन बुकिंग पेज मी तपासू शकलो नाही. संपर्काची माहिती:",
    },
    "no_contact": {
        "en": "no phone or website listed",
        "hinglish": "phone ya website listed nahi hai",
        "hi": "फ़ोन या वेबसाइट सूचीबद्ध नहीं है",
        "mr": "फोन किंवा वेबसाइट दिलेली नाही",
    },
    "no_specialist_search": {
        "en": "I can't list verified {what} yet. The kinds of places I can search are: {supported}. For a {what} you can try this Google Maps search (I have not checked these places): {url}",
        "hinglish": "Abhi main verified {what} ki list nahi de sakta. Main in jagahon ko search kar sakta hoon: {supported}. {what} ke liye aap yeh Google Maps search try kar sakte hain (maine in jagahon ko check nahi kiya hai): {url}",
        "hi": "मैं अभी सत्यापित {what} की सूची नहीं दे सकता। मैं इन जगहों को खोज सकता हूँ: {supported}। {what} के लिए आप यह Google Maps खोज आज़मा सकते हैं (मैंने इन जगहों की जाँच नहीं की है): {url}",
        "mr": "मी सध्या पडताळलेल्या {what} ची यादी देऊ शकत नाही. मी या ठिकाणांचा शोध घेऊ शकतो: {supported}. {what} साठी तुम्ही हा Google Maps शोध वापरून पाहू शकता (मी ही ठिकाणे तपासलेली नाहीत): {url}",
    },
    "contact_only_intro": {
        "en": "Only {found} of your {total} results has an online booking page, phone number or website listed. The numbers match your list:",
        "hinglish": "Aapke {total} results mein se sirf {found} ka online booking page, phone number ya website listed hai. Numbers aapki list jaise hi hain:",
        "hi": "आपके {total} नतीजों में से सिर्फ़ {found} का ऑनलाइन बुकिंग पेज, फ़ोन नंबर या वेबसाइट उपलब्ध है। नंबर आपकी सूची के अनुसार ही हैं:",
        "mr": "तुमच्या {total} निकालांपैकी फक्त {found} चे ऑनलाइन बुकिंग पेज, फोन नंबर किंवा वेबसाइट उपलब्ध आहे. क्रमांक तुमच्या यादीप्रमाणेच आहेत:",
    },
    "contact_only_none": {
        "en": "None of the {total} places in your list has a phone number, website or online booking page in the map data I use (OpenStreetMap), and I won't guess them. To get a number, tap Directions to open the place on Google Maps, or ask at the clinic. Here is what is listed:",
        "hinglish": "Aapki list ke {total} jagah mein se kisi ka bhi phone number, website ya online booking page mere map data (OpenStreetMap) mein nahi hai, aur main andaaza nahi lagaunga. Number ke liye Directions dabakar Google Maps par dekhein, ya clinic mein poochein. Jo listed hai:",
        "hi": "आपकी सूची की {total} जगहों में से किसी का भी फ़ोन नंबर, वेबसाइट या ऑनलाइन बुकिंग पेज मेरे मैप डेटा (OpenStreetMap) में नहीं है, और मैं अंदाज़ा नहीं लगाऊँगा। नंबर के लिए Directions दबाकर Google Maps पर देखें, या क्लिनिक में पूछें। जो उपलब्ध है:",
        "mr": "तुमच्या यादीतील {total} ठिकाणांपैकी कोणाचाही फोन नंबर, वेबसाइट किंवा ऑनलाइन बुकिंग पेज माझ्या नकाशा डेटामध्ये (OpenStreetMap) नाही, आणि मी अंदाज लावणार नाही. नंबरसाठी Directions दाबून Google Maps वर पहा, किंवा क्लिनिकमध्ये विचारा. जे उपलब्ध आहे:",
    },
    "online_only_next": {
        "en": "Reply with a number for booking help, or tell me another area to search.",
        "hinglish": "Booking help ke liye number bhejein, ya koi doosra area batayein.",
        "hi": "बुकिंग में मदद के लिए नंबर भेजें, या कोई दूसरा इलाका बताएँ।",
        "mr": "बुकिंगसाठी क्रमांक पाठवा, किंवा दुसरा परिसर सांगा.",
    },
}


def _t(key: str, lang: str, **kwargs) -> str:
    table = _EXTRA_TEXT[key]
    return (table.get(lang) or table["en"]).format(**kwargs)


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
    without_pin = PIN_RE.sub("", text)
    position = 0
    while locality is None:
        # Overlapping search: in "tell me nearest dermatologist in kandivali east", the first cue is
        # the pronoun "me" and its phrase is rejected, so the next cue ("in") must still be tried.
        cue = _LOCALITY_AFTER_CUE.search(without_pin, position)
        if not cue:
            break
        candidate = re.split(r"[?.!]| and | please| plz", cue.group(1), flags=re.I)[0].strip(" ,.-")
        if candidate and not _STOP_LOCALITY.fullmatch(candidate.lower()) and len(candidate) >= 3:
            if not _FACILITY_NOUN.search(candidate) and not detect_specialty(candidate):
                locality = candidate
        position = cue.start() + 1

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


def _reply(text: str, *, tier: str = "normal", facilities: Optional[list] = None, ui: Optional[str] = None,
           extra: Optional[dict] = None, quick: Optional[list] = None, trace: Optional[list] = None) -> dict:
    out = {
        "quick_replies": quick or [],
        "trace": trace or [],
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


_SHORT_SPECIALTY = {"eye": "eye care", "dental": "dental", "skin": "skin care", "ent": "ENT", "heart": "heart care",
                    "ortho": "bone and joint", "child": "children's", "women": "women's health"}


def _facility_record(position: int, place: dict, spec, area: str = "") -> dict:
    is_match = place.get("specialty_match", True)
    specialty = place.get("specialty_label") or spec.label
    if not is_match and spec.key in _SHORT_SPECIALTY:
        specialty = f"General hospital ({_SHORT_SPECIALTY[spec.key]} department not confirmed)"
    return {
        "n": position,
        "name": place.get("name"),
        "address": place.get("address") or None,
        "specialty": specialty,
        "specialty_match": bool(is_match),
        "phone": place.get("phone"),
        "website": place.get("website"),
        "maps_url": place.get("maps_url"),
        "directions_url": None if place.get("partner_demo") else directions_url(place),
        "phone_lookup_url": None if (place.get("phone") or place.get("partner_demo")) else phone_lookup_url(place, area),
        "lat": place.get("lat"),
        "lon": place.get("lon"),
        "rating": place.get("rating"),
        "open_now": place.get("open_now"),
        "source": place.get("source") or "Google Maps listing",
        "distance_km": place.get("distance_km"),
        "partner_demo": bool(place.get("partner_demo")),
        "booking": None,
    }


def _demo_place() -> dict:
    """The sandbox hospital: only shown when DEMO_PARTNER_ENABLED=1, always labelled DEMO."""
    return {
        "name": "DEMO Partner Hospital (sandbox, not a real hospital)",
        "address": "For project demonstration only. It confirms requests instantly.",
        "phone": None,
        "website": None,
        "source": "Demo partner (sandbox)",
        "place_id": "demo/partner",
        "partner_demo": True,
        "specialty_match": True,
    }


def _format_results(facilities: List[dict], spec_key: str, where: str, lang: str, source: str = "Google Maps listings") -> str:
    what = what_label(spec_key, lang)
    n = len([f for f in facilities if not f.get("partner_demo")])
    count_phrase = {
        "en": f"are {n} result{'s' if n != 1 else ''}",
        "hinglish": f"{n} result",
        "hi": f"{n} नतीजे",
        "mr": f"{n} निकाल",
    }.get(lang, f"are {n} result{'s' if n != 1 else ''}")

    real = [f for f in facilities if not f.get("partner_demo")]
    lines = [tr("results_intro", lang, what=what, where=where, count_phrase=count_phrase, source=source)]
    if len(real) < MAX_RESULTS:
        lines.append(tr("results_fewer", lang, n=len(real)))
    if lang == "en" and spec_key not in ("general",) and any(not f.get("specialty_match", True) for f in real):
        lines.append("Places that match what you asked for come first. The others are general hospitals: ask them whether they have that department.")
    if lang == "en" and len(real) > 1:
        lines.append("Ranked nearest first; places with a listed phone number are slightly preferred.")
    lines.append("")

    unlisted = tr("lbl_not_listed", lang)
    for fac in facilities:
        distance = f" - {fac['distance_km']} km" if fac.get("distance_km") is not None else ""
        lines.append(f"{fac['n']}. {fac['name']}{distance}")
        lines.append(f"   {tr('lbl_address', lang)}: {fac['address'] or unlisted}")
        if not fac.get("partner_demo"):
            lines.append(f"   {tr('lbl_phone', lang)}: {fac.get('phone') or unlisted}")
        booking = fac.get("booking") or {}
        if booking.get("status") == "found":
            lines.append(f"   {tr('lbl_booking', lang)}: {booking['url']}")
        lines.append("")

    lines.append(tr("results_next", lang))
    return "\n".join(lines)


def _demo_enabled() -> bool:
    return bool(settings.DEMO_PARTNER_ENABLED)


def _demo_only_reply(user_id: str, spec, pin, locality, lang: str, reason_text: str) -> dict:
    """Live search gave nothing usable: say so honestly, and offer only the labelled sandbox hospital."""
    facility = _facility_record(1, _demo_place(), spec, area=_where_text(pin, locality))
    save_care_state(user_id, {"stage": "results", "specialty": spec.key, "pin": pin, "locality": locality, "facilities": [facility]})
    text = (reason_text + "\n\nYou can still try the booking flow with the demo hospital below. "
            "It is a sandbox made for this project, not a real hospital.\n\nReply 1 to choose it.")
    return _reply(text, facilities=[facility], ui="facility_results", trace=["Live hospital search had no usable result", "Offered the labelled demo hospital only"])


def _outside_reply(user_id: str, spec, emergency: bool, lang: str) -> dict:
    save_care_state(user_id, {"stage": "awaiting_location", "specialty": spec.key, "emergency": emergency, "facilities": []})
    return _reply(tr("outside_maharashtra", lang), ui="ask_location", trace=["Location check: not in Maharashtra, nothing searched"])


def _run_search(user_id: str, state: dict, spec_key: str, pin, locality, lang: str, emergency: bool = False,
                extra_terms: Optional[List[str]] = None, only_local: bool = False) -> dict:
    spec = specialty_by_key(spec_key) or SPECIALTIES["general"]
    where = _where_text(pin, locality)
    what = what_label(spec.key, lang)

    # The Maps suggestion must be an English query, not the translated label.
    maps_what = what_label(spec.key, "en")

    # Maharashtra only: a PIN outside the state is refused before anything is searched.
    if pin and not is_maharashtra_pin(pin):
        return _outside_reply(user_id, spec, emergency, lang)

    # Whatever happens next, the flow is no longer "waiting for a location":
    # remember what the user told us and reset the step.
    save_care_state(user_id, {"stage": "none", "specialty": spec.key, "pin": pin, "locality": locality, "facilities": []})

    provider = _choose_provider()

    # Hand-verified entries (free; phone/website/booking exactly as the owner checked them).
    terms = extra_terms or [spec.key, (spec.label or "").lower()]
    local = local_directory.search(terms, pin, locality, limit=MAX_RESULTS)

    raw: List[dict] = []
    if not only_local:
        try:
            if provider == "google":
                if not is_configured():
                    logger.warning("PLACES_PROVIDER=google but GOOGLE_PLACES_API_KEY is not set")
                    if not local:
                        text = tr("search_not_configured", lang, what=maps_what, where=where)
                        return _demo_only_reply(user_id, spec, pin, locality, lang, text) if _demo_enabled() else _reply(text, ui="notice")
                else:
                    raw = search_places_checked(
                        _build_query(spec, pin, locality, emergency),
                        place_type=spec.place_type,
                        limit=10,
                    )
            else:
                raw = osm_search(spec.key, pin, locality, emergency=emergency, limit=10)

        except LocationNotFound:
            if not local:
                save_care_state(user_id, {**state, "stage": "awaiting_location", "specialty": spec.key, "emergency": emergency, "facilities": []})
                return _reply(tr("ask_clarify_location", lang), ui="ask_location")

        except OutsideMaharashtra:
            return _outside_reply(user_id, spec, emergency, lang)

        except PlacesUnavailable as exc:
            logger.warning("facility search unavailable (%s): %s", provider, exc)
            if not local:
                text = tr("search_unavailable", lang, what=maps_what, where=where)
                return _demo_only_reply(user_id, spec, pin, locality, lang, text) if _demo_enabled() else _reply(text, ui="notice")

    # PIN-matching map results first, then the verified entries are put in front of them.
    if pin:
        raw = sorted(raw, key=lambda p: 0 if pin in (p.get("address") or "") else 1)

    seen, seen_names, cleaned = set(), set(), []
    for place in list(local) + list(raw):
        name = (place.get("name") or "").strip()
        key = place.get("place_id") or name.lower()
        if not name or key in seen or name.lower() in seen_names:
            continue
        seen.add(key)
        seen_names.add(name.lower())
        cleaned.append(place)

    cleaned = cleaned[:MAX_RESULTS]

    if not cleaned:
        text = tr("no_results", lang, what=what, where=where)
        if _demo_enabled():
            return _demo_only_reply(user_id, spec, pin, locality, lang, text)
        save_care_state(user_id, {**state, "stage": "none", "facilities": [], "specialty": spec.key, "pin": pin, "locality": locality})
        return _reply(text, ui="notice")

    facilities = [_facility_record(i, place, spec, area=where) for i, place in enumerate(cleaned, start=1)]
    _lookup_bookings(facilities)

    # A booking page the owner verified beats anything the website scan found.
    for fac, place in zip(facilities, cleaned):
        if place.get("booking_url"):
            fac["booking"] = {"status": "found", "url": place["booking_url"], "external_provider": False, "provider_host": None}

    real_count = len(facilities)
    if _demo_enabled():
        demo = _facility_record(len(facilities) + 1, _demo_place(), spec, area=where)
        demo["booking"] = asdict(BookingInfo(status="no_website"))
        facilities.append(demo)

    save_care_state(user_id, {
        "stage": "results",
        "specialty": spec.key,
        "pin": pin,
        "locality": locality,
        "facilities": facilities,
    })

    logger.info("care search: specialty=%s results=%d", spec.key, real_count)
    source = facilities[0]["source"]
    trace = [
        "Safety check: no emergency signs in your message",
        f"Tool used: find {what} near {where} (Maharashtra only)",
        f"Found {real_count} place{'s' if real_count != 1 else ''}, ranked nearest first",
        "Waiting for you to choose a number",
    ]
    return _reply(_format_results(facilities, spec.key, where, lang, source), facilities=facilities, ui="facility_results", trace=trace)


def _choose_specialty(text: str, state: dict):
    """
    Returns (spec, unsupported_word).
      * the message names a specialty we search      -> that specialty
      * it names a kind of doctor we cannot search   -> (None, "dermatologist")
      * it says plain hospital / clinic / doctor     -> general (never the stale saved specialty)
      * no facility word at all (e.g. "book ... near Powai 400076") -> keep the saved specialty
    """
    spec = detect_specialty(text)
    if spec:
        return spec, None
    named = _SPECIALIST_NOUN.search(text or "")
    if named:
        return None, named.group(0).lower()
    if _GENERIC_FACILITY.search(text or ""):
        return SPECIALTIES["general"], None
    return specialty_by_key(state.get("specialty")) or SPECIALTIES["general"], None


def _specialist_stem(word: str) -> str:
    """'dermatologist' -> 'dermatolog' so it matches a directory entry saying 'dermatology'."""
    return re.sub(r"(ists?|ians?)$", "", (word or "").lower())


def _specialist_unsupported_reply(word: str, where: str, lang: str) -> dict:
    from urllib.parse import quote_plus
    place = where or "me"
    url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{word} near {place}")
    supported = ", ".join(sorted({(sp.label or sp.key) for sp in SPECIALTIES.values()}))
    return _reply(_t("no_specialist_search", lang, what=word, supported=supported, url=url), ui="notice")


def _is_new_place(text: str, loc: Dict[str, Optional[str]], state: dict, selected: Optional[int]) -> bool:
    """
    True when the message names a PIN/area different from the one the saved results were for.
    A PIN is trusted on its own. A bare place word needs a hospital/specialty word beside it
    and no list number, so "book hospital 2 for me tomorrow" is never read as a place.
    """
    if loc.get("pin"):
        return loc["pin"] != state.get("pin")
    if loc.get("locality") and selected is None and (detect_specialty(text) or _FACILITY_NOUN.search(text)):
        return loc["locality"].strip().lower() != (state.get("locality") or "").strip().lower()
    return False


def _online_only_reply(state: dict, facilities: List[dict], lang: str, contact_ok: bool = False) -> dict:
    """
    Filter the SAVED list. Never searches, never invents.
    contact_ok=False: only places with a verified online booking page.
    contact_ok=True : also places that list a phone number or website.
    """
    def reachable(fac: dict) -> bool:
        if (fac.get("booking") or {}).get("status") == "found":
            return True
        return contact_ok and bool(fac.get("phone") or fac.get("website"))

    shown = [f for f in facilities if reachable(f)]
    total = len(facilities)
    prefix = "contact_only" if contact_ok else "online_only"

    if shown:
        where = _where_text(state.get("pin"), state.get("locality"))
        body = _format_results(shown, state.get("specialty") or "general", where, lang, shown[0].get("source") or "")
        text = _t(f"{prefix}_intro", lang, found=len(shown), total=total) + "\n\n" + body
        return _reply(text, facilities=shown, ui="facility_results")

    lines = [_t(f"{prefix}_none", lang, total=total), ""]
    for fac in facilities:
        contact = fac.get("phone") or fac.get("website") or _t("no_contact", lang)
        lines.append(f"{fac['n']}. {fac['name']} - {contact}")
    lines += ["", _t("online_only_next", lang)]
    return _reply("\n".join(lines), facilities=facilities, ui="facility_results")


# ----------------------------------------------------------------------------
# Booking assistance
# ----------------------------------------------------------------------------

_OFFER = "\n\nDo you want me to prepare an appointment request for this hospital? Reply YES or NO."


def _booking_reply(fac: dict, lang: str) -> dict:
    name = fac["name"]
    booking = fac.get("booking") or {}

    if fac.get("partner_demo"):
        text = (f"{name}\n\nThis is a sandbox hospital made for this project. It can confirm a request instantly, "
                "so you can see the whole booking flow. No real hospital is contacted." + _OFFER)
        return _reply(text, facilities=[fac], ui="booking_link", quick=["Yes, request appointment", "No"],
                      extra={"booking_url": None, "booking_verified": False},
                      trace=[f"You chose hospital {fac['n']} (demo)", "Asking whether to prepare an appointment request"])

    # A cached "could not reach the site" deserves one retry now.
    if booking.get("status") in (None, "unreachable") and fac.get("website"):
        try:
            booking = asdict(find_booking_link(fac["website"]))
            fac["booking"] = booking
        except Exception:
            logger.exception("booking retry failed")

    extra_lines = []
    if fac.get("directions_url"):
        extra_lines.append(f"Directions: {fac['directions_url']}")
    if not fac.get("phone") and fac.get("phone_lookup_url"):
        extra_lines.append(f"Phone number not listed in my map data. You can find it on its Google Maps page: {fac['phone_lookup_url']}")
    tail = ("\n\n" + "\n".join(extra_lines) if extra_lines else "") + _OFFER

    if booking.get("status") == "found":
        if booking.get("external_provider"):
            head = tr("book_found_external", lang, name=name, url=booking["url"], host=booking.get("provider_host") or "")
        else:
            head = tr("book_found_own", lang, name=name, url=booking["url"])
        return _reply(head + tail, facilities=[fac], ui="booking_link", quick=["Yes, request appointment", "No"],
                      extra={"booking_url": booking["url"], "booking_verified": True},
                      trace=[f"You chose hospital {fac['n']}", "Found a booking page on the hospital's own website", "Asking whether to prepare an appointment request"])

    if fac.get("phone"):
        fallback = tr("book_fallback_phone", lang, phone=fac["phone"])
    elif fac.get("website"):
        fallback = tr("book_fallback_site", lang, url=fac["website"])
    else:
        fallback = tr("book_fallback_none", lang)

    return _reply(tr("book_not_found", lang, name=name, fallback=fallback) + tail, facilities=[fac], ui="booking_link",
                  quick=["Yes, request appointment", "No"], extra={"booking_url": None, "booking_verified": False},
                  trace=[f"You chose hospital {fac['n']}", "No verified online booking page found", "Asking whether to prepare an appointment request"])


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

    # 1b. Appointment-request questions (yes/no, name, phone, age, date, reason, confirmation).
    staged = appointment_flow.handle_stage(user_id, text, state)
    if staged:
        new_state, reply = staged
        save_care_state(user_id, new_state)
        return reply

    # 1c. "my appointments" / "cancel appointment HA-XXXXXX" can arrive at any time.
    if stage not in ("screening", "awaiting_location"):
        glob = appointment_flow.handle_global(user_id, text, state)
        if glob:
            new_state, reply = glob
            save_care_state(user_id, new_state)
            return reply

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

    # Does the message name a NEW PIN/area? Then the saved list is stale: search again
    # instead of re-showing it.
    place_in_text = extract_location(text)
    selected = selected_index(text, facilities) if facilities else None
    new_place = _is_new_place(text, place_in_text, state, selected)
    names_place = bool(
        place_in_text["pin"]
        or (place_in_text["locality"] and (detect_specialty(text) or _FACILITY_NOUN.search(text)))
    )

    # 4a. "only those where I can book online": filter the saved list, never re-run the search.
    if facilities and not new_place and selected is None and _ONLINE_ONLY.search(text):
        return _online_only_reply(state, facilities, lang, contact_ok=bool(_CONTACT_OK.search(text)))

    # 4b. Booking request.
    search_from_booking = False
    if is_booking_request(text):
        if not facilities:
            if not (is_facility_search(text) or names_place):
                return _reply(tr("book_need_results", lang), ui="notice")
            search_from_booking = names_place           # "book ... near Andheri East 400093" -> search first
        elif not new_place:
            idx = selected
            if idx is None:
                return _reply(tr("book_which", lang), facilities=facilities, ui="facility_results")
            if not 1 <= idx <= len(facilities):
                return _reply(tr("book_bad_index", lang, n=len(facilities)), facilities=facilities, ui="facility_results")
            chosen = facilities[idx - 1]
            reply = _booking_reply(chosen, lang)
            facilities[idx - 1] = chosen
            save_care_state(user_id, {**state, "stage": "confirm_book", "facilities": facilities, "selected": idx})
            return reply
        else:
            search_from_booking = True                  # a new area was named: saved list is stale

    # 5. A bare choice ("2", then "3") -- allowed at ANY point while a list is saved, so a number
    #    can never fall through to the AI model (which once invented a hospital called "XYZ").
    if facilities and _BARE_NUMBER.match(text):
        idx = selected_index(text, facilities)
        if idx is not None:
            if not 1 <= idx <= len(facilities):
                return _reply(tr("book_bad_index", lang, n=len(facilities)), facilities=facilities, ui="facility_results")
            reply = _booking_reply(facilities[idx - 1], lang)
            save_care_state(user_id, {**state, "stage": "confirm_book", "facilities": facilities, "selected": idx})
            return reply

    # 6. New facility search.
    if is_facility_search(text) or search_from_booking:
        spec, unsupported = _choose_specialty(text, state)
        loc = extract_location(text)
        saved = get_profile_location(user_id)
        pin = loc["pin"] or (None if loc["locality"] else saved.get("pin"))
        locality = loc["locality"] or (None if loc["pin"] else saved.get("locality"))

        if unsupported:
            stem = _specialist_stem(unsupported)
            if local_directory.search([stem], pin, locality, limit=1):
                return _run_search(user_id, {}, "general", pin, locality, lang, extra_terms=[stem], only_local=True)
            return _specialist_unsupported_reply(unsupported, _where_text(pin, locality), lang)

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
