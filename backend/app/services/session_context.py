"""
Small per-user conversation context kept in the database (table session_state):

  care_nav          current care-navigation step + the facilities last shown
                    (expires after STATE_TTL_MINUTES of inactivity)
  profile_location  PIN / locality the user told us they live in
  pref_language     language the user explicitly asked for

Only what the USER stated is stored here (a PIN they typed, a language they
chose). Nothing is inferred. Users can view and delete all of it
(GET/DELETE /api/care-navigation/state).
"""

import re
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import (
    delete_session_state,
    get_session_state,
    set_session_state,
)
from app.core.logging_config import get_logger

logger = get_logger("session_context")

STATE_TTL_MINUTES = 45

CARE_NAV = "care_nav"
PROFILE_LOCATION = "profile_location"
PREF_LANGUAGE = "pref_language"

PIN_RE = re.compile(r"(?<!\d)([1-9]\d{5})(?!\d)")

# A PIN counts as "where I live" only when the message says so.
_RESIDENCE_CUE = re.compile(
    r"\b(?:i live|i stay|i am from|im from|my (?:pin|pincode|pin code|area|location|address)|"
    r"living in|staying in|located in|rehta|rahta|rehti|rahti|rehte|rahte|meri location|mera area|"
    r"mera pin|mera pincode|maza pin|majha pin|rahto|rahte)\b|"
    r"मैं .{0,20}रहता|मैं .{0,20}रहती|मी .{0,20}राहतो|मी .{0,20}राहते|माझा पिन|मेरा पिन",
    re.I,
)


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def load_care_state(user_id: str) -> dict:
    """Current care-nav state, or {} when none / expired / unreadable."""
    try:
        state, updated = get_session_state(user_id, CARE_NAV)
    except Exception:
        logger.exception("could not load care state")
        return {}
    if not state:
        return {}
    ts = _parse_ts(updated)
    if ts and datetime.utcnow() - ts > timedelta(minutes=STATE_TTL_MINUTES):
        return {}
    return state


def save_care_state(user_id: str, state: dict) -> None:
    try:
        set_session_state(user_id, CARE_NAV, state)
    except Exception:
        logger.exception("could not save care state")


def get_profile_location(user_id: str) -> dict:
    try:
        state, _ = get_session_state(user_id, PROFILE_LOCATION)
    except Exception:
        logger.exception("could not load profile location")
        return {}
    return state or {}


def remember_location(user_id: str, message: str) -> Optional[dict]:
    """Store a PIN the user says they live at. Returns what was stored, if any."""
    if not user_id or not message:
        return None
    match = PIN_RE.search(message)
    if not match or not _RESIDENCE_CUE.search(message):
        return None
    location = {"pin": match.group(1), "source": "user_stated"}
    try:
        set_session_state(user_id, PROFILE_LOCATION, location)
    except Exception:
        logger.exception("could not save profile location")
        return None
    return location


def get_pref_language(user_id: str) -> Optional[str]:
    try:
        state, _ = get_session_state(user_id, PREF_LANGUAGE)
    except Exception:
        return None
    return (state or {}).get("language")


def set_pref_language(user_id: str, language: str) -> None:
    try:
        set_session_state(user_id, PREF_LANGUAGE, {"language": language})
    except Exception:
        logger.exception("could not save language preference")


def clear_all(user_id: str) -> None:
    delete_session_state(user_id, None)


def export_all(user_id: str) -> dict:
    """Everything stored for the user, for the 'view my data' control."""
    out = {}
    for key in (CARE_NAV, PROFILE_LOCATION, PREF_LANGUAGE):
        try:
            state, updated = get_session_state(user_id, key)
        except Exception:
            state, updated = None, None
        if state:
            out[key] = {"data": state, "updated_at": updated}
    return out


def clear_pref_language(user_id: str) -> None:
    try:
        delete_session_state(user_id, PREF_LANGUAGE)
    except Exception:
        logger.exception("could not clear language preference")
