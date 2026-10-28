"""
Google Places integration.

Gives the hospital agent real, current data instead of the empty
local `hospitals` table: name, address, phone number, website,
open-now status, rating, and a Google Maps link the user can tap
for directions or to look up online booking.

Requires GOOGLE_PLACES_API_KEY in the environment. If it is not
set, `is_configured()` returns False and the hospital agent falls
back to the local database automatically -- nothing crashes.

Get a key: https://console.cloud.google.com/google/maps-apis
Enable "Places API" (legacy) for the project the key belongs to.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# How many of the top text-search hits get a follow-up Details call
# for phone / website. Keeps this to a handful so one chat message
# doesn't fire off a dozen billed API calls.
MAX_DETAILS_LOOKUPS = 5

REQUEST_TIMEOUT_SECONDS = 6


def is_configured() -> bool:
    return bool(GOOGLE_PLACES_API_KEY)


def _place_details(place_id: str) -> dict:
    """
    Fetch phone / website / opening hours for one place.
    Returns {} on any failure -- callers just show what they have.
    """

    try:
        response = requests.get(
            DETAILS_URL,
            params={
                "place_id": place_id,
                "fields": (
                    "formatted_phone_number,international_phone_number,"
                    "website,opening_hours,url"
                ),
                "key": GOOGLE_PLACES_API_KEY,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json().get("result", {})
        return result

    except requests.RequestException:
        return {}


def _maps_search_link(name: str, address: str) -> str:
    query = requests.utils.quote(f"{name} {address}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={query}"


class PlacesUnavailable(Exception):
    """The live search could not be completed (no key, network error, quota,
    denied request). Different from "searched fine, zero results"."""


def search_places_checked(
    query: str,
    place_type: str = "hospital",
    limit: int = 6,
) -> list:
    """
    Like search_medical_places, but raises PlacesUnavailable when the search
    could not run, so callers can tell "tool failed" from "nothing found"
    and never present a failure as an empty-but-successful result.
    """

    if not is_configured():
        raise PlacesUnavailable("GOOGLE_PLACES_API_KEY is not configured")

    query = (query or "").strip()

    if not query:
        return []

    try:
        response = requests.get(
            TEXT_SEARCH_URL,
            params={
                "query": query,
                "type": place_type,
                "key": GOOGLE_PLACES_API_KEY,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()

    except (requests.RequestException, ValueError) as exc:
        raise PlacesUnavailable(type(exc).__name__) from exc

    status = payload.get("status")

    if status == "ZERO_RESULTS":
        return []

    if status != "OK":
        # OVER_QUERY_LIMIT / REQUEST_DENIED / INVALID_REQUEST etc.
        raise PlacesUnavailable(f"places status {status}")

    results = payload.get("results", [])[:limit]

    places = []

    for index, place in enumerate(results):

        name = place.get("name", "Unknown")
        address = place.get("formatted_address", "")
        rating = place.get("rating")

        open_now = None
        opening_hours = place.get("opening_hours")
        if opening_hours and "open_now" in opening_hours:
            open_now = opening_hours["open_now"]

        phone = None
        website = None
        maps_url = _maps_search_link(name, address)

        if index < MAX_DETAILS_LOOKUPS:
            details = _place_details(place.get("place_id", ""))

            phone = (
                details.get("formatted_phone_number")
                or details.get("international_phone_number")
            )
            website = details.get("website")

            if open_now is None:
                details_hours = details.get("opening_hours")
                if details_hours and "open_now" in details_hours:
                    open_now = details_hours["open_now"]

            maps_url = details.get("url") or maps_url

        places.append({
            "name": name,
            "address": address,
            "phone": phone,
            "website": website,
            "maps_url": maps_url,
            "rating": rating,
            "open_now": open_now,
            "place_type": place_type,
            "place_id": place.get("place_id"),
        })

    return places


def search_medical_places(
    query: str,
    place_type: str = "hospital",
    limit: int = 6,
) -> list:
    """
    Backward-compatible wrapper: returns [] on any failure.
    New code should use search_places_checked.
    """

    try:
        return search_places_checked(query, place_type, limit)
    except PlacesUnavailable:
        return []
