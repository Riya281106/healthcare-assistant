"""
Free hospital / clinic search using OpenStreetMap data. No API key, no account, no card.

  1. Nominatim turns a PIN code or locality into coordinates.
  2. Overpass finds hospitals / clinics around those coordinates.

HONEST LIMITS (the assistant says these to the user):
  * OpenStreetMap is community-edited. Indian hospitals are often listed without a phone
    number, website or full address, and some are missing. We show only what is in the data
    and label the rest "not listed". We never fill gaps.
  * Opening hours and availability are not used.
  * Public servers have fair-use limits: one geocode + one or two Overpass calls per search,
    with a descriptive User-Agent, short timeouts, and a small in-memory cache.
"""

import math
import re
from functools import lru_cache
from typing import List, Optional

import requests

from app.core.logging_config import get_logger
from app.services.integrations.google_places import PlacesUnavailable

logger = get_logger("osm_places")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "HealthcareAssistant/1.0 (student final-year project; hospital lookup)"
GEOCODE_TIMEOUT = 8
OVERPASS_TIMEOUT = 9     # per server; fail fast so the user is not kept waiting
NEARBY_TIMEOUT = 8
RADII_METRES = (5000, 15000)   # widen once if the first search finds too few
ENOUGH_RESULTS = 3

SOURCE_LABEL = "OpenStreetMap (community-edited map data, may be incomplete)"


class LocationNotFound(Exception):
    """The PIN / locality could not be turned into a place on the map."""


# What to look for per specialty: OSM tag values / name patterns. Name patterns are a
# fallback because many Indian clinics have a name but no speciality tag.
_SPECIALTY_NAME = {
    "eye": "eye|netra|netralaya|ophthalm|vision|drishti|nayan|optic|lasik",
    "dental": "dental|dentist|tooth|teeth|denta",
    "skin": "skin|derma|cosmet|laser clinic",
    "ent": "ent |ear nose|e\\.n\\.t|otolaryng|hearing",
    "heart": "heart|cardio|cardiac|hriday",
    "ortho": "ortho|bone|joint|spine|fracture",
    "child": "child|children|pediatric|paediatric|kids|baby|bal ",
    "women": "women|gynae|gynec|maternity|fertility|obstetric|nursing home",
}
_SPECIALTY_TAG = {
    "eye": "ophthalm",
    "dental": "dent",
    "skin": "dermat",
    "ent": "otolaryng|ent",
    "heart": "cardio",
    "ortho": "orthop",
    "child": "paediat|pediat",
    "women": "gynaec|gynec|obstet",
}


def _clean(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value or None


@lru_cache(maxsize=256)
def _geocode_cached(pin: Optional[str], locality: Optional[str]):
    params = {"format": "jsonv2", "limit": 1, "addressdetails": 0}
    if pin and not locality:
        params.update({"postalcode": pin, "country": "India"})
    else:
        params.update({"q": f"{locality or ''} {pin or ''}, India".strip(), "countrycodes": "in"})

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=GEOCODE_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise PlacesUnavailable(f"geocoder {type(exc).__name__}") from exc

    if not data:
        raise LocationNotFound(pin or locality or "")

    try:
        return float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, ValueError, TypeError) as exc:
        raise PlacesUnavailable("geocoder bad response") from exc


def geocode(pin: Optional[str], locality: Optional[str]):
    """(lat, lon) for a PIN and/or locality in India. Raises LocationNotFound / PlacesUnavailable."""
    if not pin and not locality:
        raise LocationNotFound("")
    return _geocode_cached(pin, locality)


def build_overpass_query(specialty_key: str, lat: float, lon: float, radius: int, emergency: bool) -> str:
    around = f"(around:{radius},{lat:.6f},{lon:.6f})"
    kinds = '["amenity"~"^(hospital|clinic|doctors|dentist)$"]'

    if emergency or specialty_key == "general":
        body = f'nwr{around}["amenity"="hospital"];'
    elif specialty_key == "dental":
        body = (
            f'nwr{around}["amenity"="dentist"];'
            f'nwr{around}{kinds}["name"~"{_SPECIALTY_NAME["dental"]}",i];'
        )
    else:
        tag = _SPECIALTY_TAG.get(specialty_key, "")
        name = _SPECIALTY_NAME.get(specialty_key, "")
        body = (
            f'nwr{around}{kinds}["healthcare:speciality"~"{tag}",i];'
            f'nwr{around}{kinds}["name"~"{name}",i];'
        )

    return f"[out:json][timeout:8];({body});out center tags 80;"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _http_url(value: Optional[str]) -> Optional[str]:
    value = _clean(value)
    if not value:
        return None
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    return value if re.match(r"^https?://[^\s]+\.[^\s]+$", value, re.I) else None


def _address(tags: dict) -> Optional[str]:
    street = " ".join(p for p in (_clean(tags.get("addr:housenumber")), _clean(tags.get("addr:street"))) if p)
    parts = [
        _clean(tags.get("addr:full")) or street or None,
        _clean(tags.get("addr:suburb")) or _clean(tags.get("addr:neighbourhood")),
        _clean(tags.get("addr:city")) or _clean(tags.get("addr:district")),
        _clean(tags.get("addr:postcode")),
    ]
    text = ", ".join(p for p in parts if p)
    return text or None


def parse_elements(elements: List[dict], lat: float, lon: float, emergency: bool = False) -> List[dict]:
    """Overpass elements -> place dicts, nearest first. Nameless or coordinate-less items are dropped."""
    places, seen = [], set()

    for el in elements:
        tags = el.get("tags") or {}
        name = _clean(tags.get("name")) or _clean(tags.get("name:en"))
        if not name:
            continue
        center = el.get("center") or {}
        el_lat = el.get("lat", center.get("lat"))
        el_lon = el.get("lon", center.get("lon"))
        if el_lat is None or el_lon is None:
            continue

        key = (name.lower(), round(el_lat, 3), round(el_lon, 3))
        if key in seen:
            continue
        seen.add(key)

        distance = _haversine_km(lat, lon, el_lat, el_lon)
        phone = _clean(tags.get("phone")) or _clean(tags.get("contact:phone")) or _clean(tags.get("contact:mobile"))

        places.append({
            "name": name,
            "address": _address(tags),
            "phone": phone,
            "website": _http_url(tags.get("website") or tags.get("contact:website")),
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={el_lat:.6f},{el_lon:.6f}",
            "rating": None,
            "open_now": None,
            "place_type": tags.get("amenity", "hospital"),
            "place_id": f"{el.get('type', 'node')}/{el.get('id')}",
            "source": SOURCE_LABEL,
            "distance_km": round(distance, 1),
            "_emergency": (tags.get("emergency") or "").lower() == "yes",
        })

    places.sort(key=lambda p: ((0 if (emergency and p["_emergency"]) else 1), p["distance_km"]))
    for p in places:
        p.pop("_emergency", None)
    return places


def _describe(exc: Exception) -> str:
    """Short, loggable description including the HTTP status when there is one."""
    response = getattr(exc, "response", None)
    if response is not None:
        snippet = (response.text or "")[:120].replace("\n", " ")
        return f"{type(exc).__name__} status={response.status_code} body={snippet!r}"
    return type(exc).__name__


def _run_overpass(query: str) -> List[dict]:
    last_error = None
    for url in OVERPASS_URLS:
        try:
            resp = requests.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=OVERPASS_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logger.warning("overpass %s failed: %s", url, _describe(exc))
    raise PlacesUnavailable(f"overpass {type(last_error).__name__}")


# Search words for the Nominatim fallback (used only when every Overpass server fails).
_NEARBY_TERM = {
    "eye": "eye hospital", "dental": "dentist", "skin": "skin clinic", "ent": "ENT hospital",
    "heart": "heart hospital", "ortho": "orthopedic hospital", "child": "children hospital",
    "women": "maternity hospital", "general": "hospital",
}
_HEALTH_CLASSES = {"amenity", "healthcare"}
_HEALTH_TYPES = {"hospital", "clinic", "doctors", "dentist", "doctor", "nursing_home", "centre", "optician"}


def parse_nominatim_results(results: List[dict], lat: float, lon: float) -> List[dict]:
    """Nominatim search results -> place dicts (same shape as parse_elements), nearest first."""
    places, seen = [], set()
    for r in results:
        if (r.get("category") or r.get("class")) not in _HEALTH_CLASSES or r.get("type") not in _HEALTH_TYPES:
            continue
        name = _clean(r.get("name")) or _clean((r.get("display_name") or "").split(",")[0])
        try:
            r_lat, r_lon = float(r["lat"]), float(r["lon"])
        except (KeyError, ValueError, TypeError):
            continue
        if not name:
            continue
        key = (name.lower(), round(r_lat, 3), round(r_lon, 3))
        if key in seen:
            continue
        seen.add(key)

        extra = r.get("extratags") or {}
        addr = r.get("address") or {}
        parts = [addr.get("road"), addr.get("suburb") or addr.get("neighbourhood"),
                 addr.get("city") or addr.get("town") or addr.get("state_district"), addr.get("postcode")]
        address = ", ".join(p for p in parts if p) or None
        phone = _clean(extra.get("phone")) or _clean(extra.get("contact:phone"))

        places.append({
            "name": name,
            "address": address,
            "phone": phone,
            "website": _http_url(extra.get("website") or extra.get("contact:website")),
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={r_lat:.6f},{r_lon:.6f}",
            "rating": None,
            "open_now": None,
            "place_type": r.get("type", "hospital"),
            "place_id": f"{r.get('osm_type', 'node')}/{r.get('osm_id')}",
            "source": SOURCE_LABEL,
            "distance_km": round(_haversine_km(lat, lon, r_lat, r_lon), 1),
        })
    places.sort(key=lambda p: p["distance_km"])
    return places


def _nominatim_nearby(specialty_key: str, lat: float, lon: float, radius_m: int = 10000) -> List[dict]:
    d_lat = radius_m / 111_000
    d_lon = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.2))
    params = {
        "q": _NEARBY_TERM.get(specialty_key, "hospital"),
        "format": "jsonv2", "limit": 20, "extratags": 1, "addressdetails": 1,
        "viewbox": f"{lon - d_lon:.5f},{lat + d_lat:.5f},{lon + d_lon:.5f},{lat - d_lat:.5f}",
        "bounded": 1,
    }
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=NEARBY_TIMEOUT)
        resp.raise_for_status()
        return parse_nominatim_results(resp.json(), lat, lon)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("nominatim nearby failed: %s", _describe(exc))
        raise PlacesUnavailable(f"nominatim {type(exc).__name__}") from exc


def search_facilities(
    specialty_key: str,
    pin: Optional[str],
    locality: Optional[str],
    emergency: bool = False,
    limit: int = 10,
) -> List[dict]:
    """Nearest matching facilities. Raises LocationNotFound or PlacesUnavailable."""
    lat, lon = geocode(pin, locality)

    places: List[dict] = []
    try:
        for radius in RADII_METRES:
            elements = _run_overpass(build_overpass_query(specialty_key, lat, lon, radius, emergency))
            places = parse_elements(elements, lat, lon, emergency)
            if len(places) >= ENOUGH_RESULTS:
                break
    except PlacesUnavailable:
        # Every Overpass server failed: try the geocoder's own category search instead.
        logger.warning("overpass unavailable, falling back to nominatim nearby search")
        places = _nominatim_nearby("general" if emergency else specialty_key, lat, lon)

    return places[:limit]
