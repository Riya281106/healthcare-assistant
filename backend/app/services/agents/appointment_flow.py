"""
APPOINTMENT REQUEST FLOW  (controlled state machine, no LLM decides anything here)

    hospital chosen -> "Do you want to request an appointment?"
        yes -> 5 short questions, ONE at a time:  name, phone, age, date/time, reason
            -> summary  -> "YES to confirm" (or change one thing / cancel)
                yes -> saved as an appointment REQUEST (details encrypted at rest)

Honesty rules, enforced in code:
  * Hospitals in India have no public booking API, so a real hospital's request is saved with
    the status "requested" and the person is told to call and confirm. Never "booked".
  * Only the clearly labelled DEMO partner hospital (a sandbox built for this project) confirms
    instantly, and its reply says it is a demonstration.
  * Nothing is saved until the person says YES on the summary screen.
  * Every write is the person's own: a request can only be read or cancelled by its owner.

The emergency detector runs BEFORE this module (orchestrator), so "chest pain" typed while
answering a question still gets the emergency reply.
"""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

from app.core.database import (
    cancel_appointment,
    create_appointment,
    get_appointment,
    get_user_profile,
    list_appointments,
)
from app.core.logging_config import get_logger
from app.services.facilities.links import directions_url, phone_lookup_url

logger = get_logger("appointment_flow")

IST = timezone(timedelta(hours=5, minutes=30))
MAX_DAYS_AHEAD = 60
STEPS = ("name", "phone", "age", "when", "reason")
STAGES = ("confirm_book", "collect", "confirm_summary", "confirm_cancel")

_YES = re.compile(r"^\s*(?:yes|yeah|yep|yup|y|ok|okay|sure|confirm|confirmed|haan|han|haa|ha|hanji|ji haan|हाँ|हां|हा|होय|हो|जी हाँ)\b", re.I)
_NO = re.compile(r"^\s*(?:no|nope|nah|n|nahi|nahin|nhi|na|नहीं|नही|नाही|ना)\b", re.I)
_STOP = re.compile(r"^\s*(?:cancel|stop|quit|exit|abort|never ?mind|forget it|go back|back|reset)\s*[.!]*\s*$", re.I)
_SAME = re.compile(r"^\s*(?:same|same as profile|use (?:it|that|same)|yes|haan|ok|okay)\s*[.!]*\s*$", re.I)
_SKIP = re.compile(r"^\s*(?:skip|none|no reason|-)\s*[.!]*\s*$", re.I)

_REF = re.compile(r"\bHA-[A-Z2-9]{6}\b", re.I)
_MY_APPOINTMENTS = re.compile(
    r"\b(?:my|show|view|list|see|check)\b.{0,25}\bappointments?\b|\bappointments? (?:list|history|status)\b|\bmy bookings?\b", re.I
)
_CANCEL_APPT = re.compile(r"\bcancel\b.{0,40}\b(?:appointment|booking|request|HA-[A-Z2-9]{6})\b|\b(?:HA-[A-Z2-9]{6})\b.{0,30}\bcancel\b", re.I)
_CHANGE = re.compile(r"\b(?:change|edit|wrong|correct|update|fix|modify)\b", re.I)


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def today() -> date:
    """Today's date in India. A function so tests can pin it."""
    return datetime.now(IST).date()


def _reply(text: str, *, ui: str = "text", quick: Optional[list] = None, facilities=None,
           appointment: Optional[dict] = None, trace: Optional[list] = None) -> dict:
    return {
        "response": text,
        "urgency_tier": "normal",
        "agent": "CARE_NAVIGATOR",
        "rag_used": False,
        "sources": [],
        "facilities": facilities or [],
        "ui": ui,
        "quick_replies": quick or [],
        "appointment": appointment,
        "trace": trace or [],
    }


def _fmt_date(d: date) -> str:
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b %Y')}"


def _fmt_phone(digits: str) -> str:
    return f"+91 {digits[:5]} {digits[5:]}"


# ----------------------------------------------------------------------------
# Validators: each returns (value, error_message). error_message is None when valid.
# ----------------------------------------------------------------------------

_NAME_OK = re.compile(r"^[A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F .'\-]{1,59}$")


def parse_name(text: str) -> Tuple[Optional[str], Optional[str]]:
    value = re.sub(r"\s+", " ", (text or "").strip())
    value = re.sub(r"^(?:my name is|name is|i am|i'm|this is|mera naam|maza naam|majha naam)\s+", "", value, flags=re.I).strip(" .")
    if not _NAME_OK.match(value) or len(re.findall(r"[A-Za-z\u0900-\u097F]", value)) < 2 or _YES.match(value) or _NO.match(value):
        return None, "That doesn't look like a name. Please type the patient's full name using letters only (for example Riya Sharma)."
    return value.title() if value.isascii() else value, None


def parse_phone(text: str) -> Tuple[Optional[str], Optional[str]]:
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return digits, None
    return None, "Please give a 10-digit Indian mobile number, for example 98765 43210."


def parse_age(text: str) -> Tuple[Optional[int], Optional[str]]:
    match = re.search(r"\b(\d{1,3})\b", text or "")
    if not match:
        return None, "Please type the age as a number, for example 34."
    age = int(match.group(1))
    if re.search(r"\b(?:month|months|mahine|mahina|महीने)\b", text or "", re.I) and age <= 36:
        return 0, None
    if 0 <= age <= 120:
        return age, None
    return None, "That age doesn't look right. Please type the age in years, for example 34."


_WEEKDAYS = {"monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
             "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6}
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
           "oct": 10, "nov": 11, "dec": 12}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))


def _parse_slot(t: str) -> Optional[str]:
    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", t)
    if time_match:
        hour, minute, ampm = int(time_match.group(1)), time_match.group(2) or "00", time_match.group(3).upper()
        if 1 <= hour <= 12:
            return f"{hour}:{minute} {ampm}"
    if re.search(r"\b(?:morning|subah|subha|sakal|savere)\b|सुबह|सकाळ", t):
        return "morning"
    if re.search(r"\b(?:afternoon|dopahar|dupar|dupari)\b|दोपहर|दुपार", t):
        return "afternoon"
    if re.search(r"\b(?:evening|shaam|sham|sandhya|sandhyakal)\b|शाम|संध्याकाळ", t):
        return "evening"
    return None


def parse_when(text: str, base: Optional[date] = None) -> Tuple[Optional[date], Optional[str], Optional[str]]:
    """(date, slot, error). A date is required; a time of day is optional."""
    base = base or today()
    t = (text or "").lower()
    slot = _parse_slot(t)
    found: Optional[date] = None

    try:
        if re.search(r"\byesterday\b", t):
            return None, slot, "That date has already passed. Please choose today or a later day."
        if re.search(r"\bday after tomorrow\b|\bparso\b", t):
            found = base + timedelta(days=2)
        elif re.search(r"\btomorrow\b|\btmrw\b|\btomorow\b|\btmw\b|\bkal\b|\budya\b|कल|उद्या", t):
            found = base + timedelta(days=1)
        elif re.search(r"\btoday\b|\baaj\b|\baj\b|आज", t):
            found = base
        elif re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
            y, m, d = map(int, re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t).groups())
            found = date(y, m, d)
        elif re.search(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b", t):
            d, m, y = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b", t).groups()
            d, m = int(d), int(m)
            if y:
                year = int(y) + (2000 if len(y) == 2 else 0)
                found = date(year, m, d)
            else:
                found = date(base.year, m, d)
                if found < base:
                    found = date(base.year + 1, m, d)
        elif re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s+)?({_MONTH_RE})[a-z]*\b", t):
            d, mon = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s+)?({_MONTH_RE})[a-z]*\b", t).groups()
            found = date(base.year, _MONTHS[mon], int(d))
            if found < base:
                found = date(base.year + 1, _MONTHS[mon], int(d))
        elif re.search(rf"\b({_MONTH_RE})[a-z]*\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", t):
            mon, d = re.search(rf"\b({_MONTH_RE})[a-z]*\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", t).groups()
            found = date(base.year, _MONTHS[mon], int(d))
            if found < base:
                found = date(base.year + 1, _MONTHS[mon], int(d))
        else:
            for word, weekday in _WEEKDAYS.items():
                if re.search(rf"\b{word}\b", t):
                    ahead = (weekday - base.weekday()) % 7
                    found = base + timedelta(days=ahead or 7)
                    break
    except ValueError:
        return None, slot, "That date doesn't exist. Please give the day again, for example tomorrow, 5 Nov or Monday."

    if found is None:
        return None, slot, "Which day would you like? For example: tomorrow morning, 5 Nov evening or Monday 11am."
    if found < base:
        return None, slot, "That date has already passed. Please choose today or a later day."
    if found > base + timedelta(days=MAX_DAYS_AHEAD):
        return None, slot, f"I can only take requests up to {MAX_DAYS_AHEAD} days ahead. Please choose an earlier day."
    return found, slot, None


def parse_reason(text: str, default: str) -> Tuple[Optional[str], Optional[str]]:
    value = re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f]", " ", text or "")).strip()
    if _SKIP.match(value):
        return default, None
    if len(value) < 3:
        return None, f"Please describe the reason in a few words (or type skip to use \"{default}\")."
    return value[:200], None


# ----------------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------------

def _profile_defaults(user_id: str) -> dict:
    try:
        profile = get_user_profile(int(user_id)) or {}
    except Exception:
        return {}
    profile = dict(profile) if not isinstance(profile, dict) else profile
    out = {}
    if profile.get("name"):
        out["name"] = str(profile["name"])
    digits = re.sub(r"\D", "", str(profile.get("phone") or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 10 and digits[0] in "6789":
        out["phone"] = digits
    if isinstance(profile.get("age"), int) and 0 <= profile["age"] <= 120:
        out["age"] = profile["age"]
    return out


def _prompt(step: str, appt: dict, defaults: dict, first: bool = False) -> dict:
    n = STEPS.index(step) + 1
    head = f"Step {n} of {len(STEPS)}. "
    quick: list = []
    if step == "name":
        text = head + "What is the patient's full name?"
        if defaults.get("name"):
            text += f" (Reply \"same\" to use {defaults['name']}.)"
            quick = ["Same"]
    elif step == "phone":
        text = head + "Which mobile number can the hospital call you on? (10 digits)"
        if defaults.get("phone"):
            text += f" (Reply \"same\" to use {_fmt_phone(defaults['phone'])}.)"
            quick = ["Same"]
    elif step == "age":
        text = head + "What is the patient's age in years?"
        if defaults.get("age") is not None:
            text += f" (Reply \"same\" to use {defaults['age']}.)"
            quick = ["Same"]
    elif step == "when":
        text = head + "When would you like to visit? For example: tomorrow morning, 5 Nov evening, or Monday 11am."
        quick = ["Tomorrow morning", "Tomorrow evening"]
    else:
        text = head + f"What is the visit for, in a few words? (Reply \"skip\" to use \"{appt['default_reason']}\".)"
        quick = ["Skip"]
    if first:
        text += "\n\nYou can type CANCEL at any time to stop. Nothing is saved until you confirm at the end."
    return _reply(text, ui="appointment_form", quick=quick + ["Cancel"],
                  trace=[f"Collecting appointment details ({n}/{len(STEPS)}): {step}"])


def _summary(appt: dict) -> dict:
    v = appt["values"]
    fac = appt["facility"]
    d = date.fromisoformat(v["date"])
    when = _fmt_date(d) + (f", {v['slot']}" if v.get("slot") else "")
    age = f"{v['age']} years" if v["age"] else "under 1 year / not given"
    lines = [
        "Please check your appointment request:",
        "",
        f"Hospital: {fac['name']}",
        f"Address: {fac.get('address') or 'not listed'}",
        f"Patient: {v['name']}, {age}",
        f"Phone: {_fmt_phone(v['phone'])}",
        f"Visit: {when}",
        f"Reason: {v['reason']}",
        "",
        "Reply YES to confirm, or tell me what to change (name, phone, age, date, reason). Reply CANCEL to stop.",
    ]
    return _reply("\n".join(lines), ui="appointment_summary", quick=["Yes, confirm", "Change something", "Cancel"],
                  trace=["All details collected", "Waiting for your confirmation before saving anything"])


# ----------------------------------------------------------------------------
# Start (called by the care navigator once a hospital is chosen and the person says yes)
# ----------------------------------------------------------------------------

def begin(user_id: str, state: dict, fac: dict, specialty_label: str) -> Tuple[dict, dict]:
    """Returns (new_state, reply) for the first question."""
    appt = {
        "facility": {k: fac.get(k) for k in ("n", "name", "address", "phone", "source", "partner_demo", "lat", "lon", "maps_url")},
        "step": "name",
        "values": {},
        "default_reason": f"{specialty_label} consultation",
        "edit": False,
    }
    new_state = {**state, "stage": "collect", "appt": appt}
    return new_state, _prompt("name", appt, _profile_defaults(user_id), first=True)


# ----------------------------------------------------------------------------
# Stage handler
# ----------------------------------------------------------------------------

def _abort(state: dict, text: str = "Okay, I've stopped. Nothing was saved. You can pick another hospital number from the list, or tell me a different area.") -> Tuple[dict, dict]:
    new_state = {k: v for k, v in state.items() if k != "appt"}
    new_state["stage"] = "results" if state.get("facilities") else "none"
    return new_state, _reply(text, ui="text", trace=["Appointment request stopped: nothing saved"])


def _accept(step: str, text: str, appt: dict, defaults: dict):
    """(value, error) for one step."""
    if step == "name":
        if _SAME.match(text) and defaults.get("name"):
            return defaults["name"], None
        return parse_name(text)
    if step == "phone":
        if _SAME.match(text) and defaults.get("phone"):
            return defaults["phone"], None
        return parse_phone(text)
    if step == "age":
        if _SAME.match(text) and defaults.get("age") is not None:
            return defaults["age"], None
        return parse_age(text)
    if step == "reason":
        return parse_reason(text, appt["default_reason"])
    return None, "Sorry, something went wrong with that question."


def _finish(user_id: str, state: dict) -> Tuple[dict, dict]:
    appt = state["appt"]
    v, fac = appt["values"], appt["facility"]
    demo = bool(fac.get("partner_demo"))
    slot = v.get("slot")

    if demo:
        slot = {"morning": "10:00 AM", "afternoon": "2:00 PM", "evening": "5:30 PM"}.get(slot, slot) or "10:00 AM"
        status = "confirmed"
    else:
        status = "requested"

    saved = create_appointment(
        user_id,
        {
            "facility_name": fac["name"],
            "facility_address": fac.get("address"),
            "facility_phone": fac.get("phone"),
            "facility_source": fac.get("source"),
            "is_demo": demo,
            "patient_name": v["name"],
            "patient_phone": v["phone"],
            "patient_age": v["age"],
            "preferred_date": v["date"],
            "preferred_slot": slot,
            "reason": v["reason"],
        },
        status=status,
    )

    when = _fmt_date(date.fromisoformat(v["date"])) + (f", {slot}" if slot else "")
    lines = [f"Saved. Your reference number is {saved['ref']}.", "", f"Hospital: {fac['name']}", f"Patient: {v['name']}", f"Visit: {when}"]

    if demo:
        lines += [
            "",
            "Status: CONFIRMED (demo hospital).",
            "This is a sandbox hospital made for this project. No real hospital was contacted and no real appointment exists.",
        ]
    else:
        lines += [
            "",
            "Status: REQUESTED. The hospital has NOT confirmed this yet, and I can't contact it for you.",
        ]
        if fac.get("phone"):
            lines.append(f"Next step: call {fac['phone']} and ask for OPD or appointment booking.")
        else:
            link = phone_lookup_url(fac)
            lines.append("Next step: this hospital has no phone number in my map data. " +
                         (f"Open its Google Maps listing to find one: {link}" if link else "Look it up on Google Maps."))
        script = (f"Hello, I would like an appointment for {v['name']} on {when}. Reason: {v['reason']}. "
                  f"My number is {_fmt_phone(v['phone'])}. (My reference: {saved['ref']})")
        lines += ["", "What you can say when you call:", f"\"{script}\""]

    route = directions_url(fac)
    if route:
        lines += ["", f"Directions: {route}"]
    lines += ["", f"To see your requests say \"my appointments\". To cancel, say \"cancel appointment {saved['ref']}\"."]

    new_state = {k: v2 for k, v2 in state.items() if k != "appt"}
    new_state["stage"] = "results" if state.get("facilities") else "none"
    return new_state, _reply("\n".join(lines), ui="appointment_confirmed", appointment=saved,
                             quick=["My appointments"],
                             trace=[f"Saved appointment request {saved['ref']} (details encrypted)", f"Status: {status}"])


def handle_stage(user_id: str, text: str, state: dict) -> Optional[Tuple[dict, dict]]:
    """
    Returns (new_state, reply) when the message belongs to the appointment flow, or None to let the
    normal navigator handle it (for example a different hospital number while a yes/no is pending).
    """
    stage = state.get("stage")
    text = (text or "").strip()

    # ---- cancelling an existing request
    if stage == "confirm_cancel":
        ref = state.get("cancel_ref")
        base = {k: v for k, v in state.items() if k not in ("cancel_ref",)}
        base["stage"] = "results" if state.get("facilities") else "none"
        if _YES.match(text):
            done = cancel_appointment(user_id, ref)
            if not done:
                return base, _reply("I couldn't cancel that request; it may already be cancelled.")
            return base, _reply(f"Done. Request {ref} at {done['facility_name']} is cancelled. If you already called the hospital, please tell them too.",
                                trace=[f"Cancelled {ref}"])
        return base, _reply("Okay, I've kept it as it is.")

    if stage == "confirm_book":
        if _YES.match(text):
            facs = state.get("facilities") or []
            idx = state.get("selected")
            if not idx or not 1 <= idx <= len(facs):
                return _abort(state, "Let's pick a hospital first. Reply with its number from the list.")
            from app.services.facilities.specialty import specialty_by_key, SPECIALTIES
            spec = specialty_by_key(state.get("specialty")) or SPECIALTIES["general"]
            return begin(user_id, state, facs[idx - 1], spec.label.split(" / ")[0])
        if _NO.match(text) or _STOP.match(text):
            return _abort(state, "No problem. Pick another number from the list whenever you're ready, or tell me a different area.")
        return None   # a new number, a new search, or something unrelated: not ours

    if stage not in ("collect", "confirm_summary"):
        return None

    appt = state.get("appt")
    if not appt:
        return _abort(state)

    if _STOP.match(text):
        return _abort(state)

    defaults = _profile_defaults(user_id)

    # ---- summary screen
    if stage == "confirm_summary":
        if _YES.match(text):
            return _finish(user_id, state)
        if _NO.match(text):
            return _abort(state)
        wanted = None
        for key, words in (("name", r"\bname\b"), ("phone", r"\b(?:phone|mobile|number)\b"), ("age", r"\bage\b"),
                           ("when", r"\b(?:date|day|time|when)\b"), ("reason", r"\b(?:reason|problem|visit)\b")):
            if re.search(words, text, re.I):
                wanted = key
                break
        if wanted:
            appt = {**appt, "step": wanted, "edit": True}
            return {**state, "stage": "collect", "appt": appt}, _prompt(wanted, appt, defaults)
        if _CHANGE.search(text):
            return state, _reply("What would you like to change?", ui="appointment_form",
                                 quick=["Name", "Phone", "Age", "Date", "Reason", "Cancel"])
        return state, _reply("Please reply YES to confirm, tell me what to change, or reply CANCEL.", ui="appointment_summary",
                             quick=["Yes, confirm", "Change something", "Cancel"])

    # ---- collecting answers
    step = appt["step"]
    values = dict(appt["values"])

    if step == "when":
        d, slot, error = parse_when(text)
        if error:
            return state, _reply(error, ui="appointment_form", quick=["Tomorrow morning", "Cancel"])
        values["date"], values["slot"] = d.isoformat(), slot
    else:
        value, error = _accept(step, text, appt, defaults)
        if error:
            return state, _reply(error, ui="appointment_form", quick=(["Same"] if defaults.get(step) is not None else []) + ["Cancel"])
        values[step] = value

    appt = {**appt, "values": values}

    if appt.get("edit"):
        appt["edit"] = False
        new_state = {**state, "stage": "confirm_summary", "appt": appt}
        return new_state, _summary(appt)

    next_index = STEPS.index(step) + 1
    if next_index >= len(STEPS):
        new_state = {**state, "stage": "confirm_summary", "appt": appt}
        return new_state, _summary(appt)

    appt["step"] = STEPS[next_index]
    return {**state, "stage": "collect", "appt": appt}, _prompt(appt["step"], appt, defaults)


# ----------------------------------------------------------------------------
# Messages that can arrive at any time: "my appointments", "cancel appointment HA-XXXXXX"
# ----------------------------------------------------------------------------

def _line(a: dict) -> str:
    when = _fmt_date(date.fromisoformat(a["preferred_date"])) if a.get("preferred_date") else "date not set"
    slot = f", {a['preferred_slot']}" if a.get("preferred_slot") else ""
    demo = " [DEMO]" if a.get("is_demo") else ""
    return f"{a['ref']}  {a['facility_name']}{demo}  {when}{slot}  [{a['status'].upper()}]"


def handle_global(user_id: str, text: str, state: dict) -> Optional[Tuple[dict, dict]]:
    text = (text or "").strip()

    if _CANCEL_APPT.search(text):
        ref_match = _REF.search(text)
        mine = list_appointments(user_id, limit=20)
        active = [a for a in mine if a["status"] in ("requested", "confirmed")]
        if ref_match:
            appt = get_appointment(user_id, ref_match.group(0))
            if not appt:
                return state, _reply("I can't find an appointment request with that reference in your account.")
            if appt["status"] == "cancelled":
                return state, _reply(f"Request {appt['ref']} is already cancelled.")
        elif len(active) == 1:
            appt = active[0]
        elif not active:
            return state, _reply("You have no active appointment requests to cancel.")
        else:
            lines = ["Which one would you like to cancel? Reply with its reference, for example \"cancel appointment " + active[0]["ref"] + "\":", ""]
            lines += [_line(a) for a in active[:5]]
            return state, _reply("\n".join(lines), ui="appointment_list")
        new_state = {**state, "stage": "confirm_cancel", "cancel_ref": appt["ref"]}
        return new_state, _reply(
            f"Cancel request {appt['ref']} at {appt['facility_name']}? Reply YES to cancel or NO to keep it.",
            ui="appointment_form", quick=["Yes, cancel it", "No, keep it"])

    if _MY_APPOINTMENTS.search(text):
        mine = list_appointments(user_id, limit=5)
        if not mine:
            return state, _reply("You don't have any appointment requests yet. Tell me what you need, for example \"eye hospital near Dadar, Mumbai\".")
        lines = ["Your latest appointment requests:", ""] + [_line(a) for a in mine]
        lines += ["", "REQUESTED means the hospital has not confirmed yet: please call them. To cancel, say \"cancel appointment <reference>\"."]
        return state, _reply("\n".join(lines), ui="appointment_list", trace=["Looked up your own appointment requests"])

    return None
