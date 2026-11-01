"""
Links that help a person reach a facility. All of them are built from data the search already
returned; nothing here looks anything up or guesses a phone number.
"""

from typing import Optional
from urllib.parse import quote_plus

_MAPS_DIR = "https://www.google.com/maps/dir/?api=1&destination="
_MAPS_SEARCH = "https://www.google.com/maps/search/?api=1&query="


def directions_url(place: dict) -> Optional[str]:
    """Turn-by-turn directions in Google Maps: exact coordinates when known, else name + address."""
    lat, lon = place.get("lat"), place.get("lon")
    if lat is not None and lon is not None:
        return f"{_MAPS_DIR}{float(lat):.6f},{float(lon):.6f}"
    name = (place.get("name") or "").strip()
    if not name:
        return None
    address = (place.get("address") or "").strip()
    return _MAPS_DIR + quote_plus(f"{name} {address}".strip())


def phone_lookup_url(place: dict, area: str = "") -> Optional[str]:
    """Opens the place's Google Maps listing, which usually shows its phone number."""
    name = (place.get("name") or "").strip()
    if not name:
        return None
    where = (place.get("address") or area or "").strip()
    return _MAPS_SEARCH + quote_plus(f"{name} {where}".strip())
