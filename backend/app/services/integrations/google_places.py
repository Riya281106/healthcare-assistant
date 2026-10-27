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


def search_medical_places(
    query: str,
    place_type: str = "hospital",
    limit: int = 6,
) -> list:
    """
    Search Google Places (Text Search) for hospitals / clinics /
    pharmacies matching `query` (a free-text location description,
    e.g. "hospitals in Andheri Mumbai" or "clinics near Dadar
    Mumbai"). Returns a list of dicts:

        {
            "name": str,
            "address": str,
            "phone": str | None,
            "website": str | None,
            "maps_url": str,
            "rating": float | None,
            "open_now": bool | None,
            "place_type": str,
        }

    Returns [] if the API key is missing, the request fails, or
    there are no matches -- callers should treat that as "fall
    back to the local database", not as an error to surface raw.
    """

    if not is_configured():
        return []

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

    except requests.RequestException:
        return []

    status = payload.get("status")

    if status not in ("OK", "ZERO_RESULTS"):
        # OVER_QUERY_LIMIT / REQUEST_DENIED / INVALID_REQUEST etc.
        # -- treat as "unavailable right now", not a hard error.
        return []

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

            maps_url = details.get("url") or _maps_search_link(name, address)

        else:
            maps_url = _maps_search_link(name, address)

        places.append({
            "name": name,
            "address": address,
            "phone": phone,
            "website": website,
            "maps_url": maps_url,
            "rating": rating,
            "open_now": open_now,
            "place_type": place_type,
        })

    return places
