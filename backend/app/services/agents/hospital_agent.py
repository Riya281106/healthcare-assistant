from app.core.database import search_hospitals
from app.services.integrations.google_places import (
    is_configured,
    search_medical_places,
)


# ==================================================
# EXTRACT LOCATION DETAILS
# ==================================================

KNOWN_CITIES = [
    "mumbai",
    "delhi",
    "pune",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "kolkata",
    "ahmedabad",
    "jaipur",
    "lucknow",
    "surat",
    "nagpur",
]

KNOWN_AREAS = {
    "andheri": "Andheri",
    "bandra": "Bandra",
    "dadar": "Dadar",
    "powai": "Powai",
    "borivali": "Borivali",
    "thane": "Thane",
    "worli": "Worli",
    "juhu": "Juhu",
}


def extract_location(message: str):
    """
    Extract city and area information from the user's
    hospital-related request.
    """

    message_lower = message.lower()

    city = None
    area = None

    for known_city in KNOWN_CITIES:
        if known_city in message_lower:
            city = known_city.title()
            break

    for key, value in KNOWN_AREAS.items():
        if key in message_lower:
            area = value
            break

    return {"city": city, "area": area}


# ==================================================
# CHECK EMERGENCY / BOOKING REQUEST
# ==================================================

EMERGENCY_KEYWORDS = [
    "emergency hospital",
    "emergency",
    "urgent hospital",
    "24 hour hospital",
    "24-hour hospital",
    "emergency care",
    "ambulance",
]

BOOKING_KEYWORDS = [
    "book",
    "booking",
    "appointment",
    "schedule a visit",
    "make an appointment",
]

CLINIC_KEYWORDS = ["clinic", "pharmacy", "chemist", "diagnostic", "lab"]


def is_emergency_hospital_request(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in EMERGENCY_KEYWORDS)


def is_booking_request(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in BOOKING_KEYWORDS)


def guess_place_type(message: str) -> str:
    """
    Decide whether this reads more like a clinic/pharmacy request
    than a hospital request, so the Places search targets the
    right category.
    """

    message_lower = message.lower()

    if any(keyword in message_lower for keyword in CLINIC_KEYWORDS):
        return "doctor"

    return "hospital"


# ==================================================
# FORMAT RESULTS -- LIVE (GOOGLE PLACES) DATA
# ==================================================

def format_live_places(places: list, booking_requested: bool) -> str:

    lines = ["Here's what I found nearby:\n"]

    for place in places:

        lines.append(f"• {place['name']}")

        if place["address"]:
            lines.append(f"  Address: {place['address']}")

        if place["phone"]:
            lines.append(f"  Phone: {place['phone']}")

        if place["rating"]:
            lines.append(f"  Rating: {place['rating']} / 5")

        if place["open_now"] is not None:
            lines.append(
                f"  Currently: {'Open' if place['open_now'] else 'Closed'}"
            )

        if place["website"]:
            lines.append(f"  Website: {place['website']}")

        lines.append(f"  Directions: {place['maps_url']}")

        lines.append("")

    if booking_requested:
        lines.append(
            "To book: call the number directly, or open the website "
            "link above if they list online booking -- I can't place "
            "the appointment for you from here, but the phone number "
            "and site are the fastest way to lock one in. Tap "
            "\"Directions\" for the exact location on the map."
        )
    else:
        lines.append(
            "Tap a phone number to call, or \"Directions\" to open the "
            "location in Maps."
        )

    return "\n".join(lines)


# ==================================================
# FORMAT RESULTS -- LOCAL DATABASE FALLBACK
# ==================================================

def format_local_hospitals(hospitals: list) -> str:

    lines = [
        "Here's what I have in the local hospital list "
        "(live search is not configured, so this may not be "
        "complete or current):\n"
    ]

    for hospital in hospitals:

        lines.append(f"• {hospital['name']}")

        if hospital["area"]:
            lines.append(f"  Area: {hospital['area']}")

        if hospital["address"]:
            lines.append(f"  Address: {hospital['address']}")

        if hospital["phone"]:
            lines.append(f"  Phone: {hospital['phone']}")

        lines.append(
            f"  Emergency Available: {hospital['emergency_available']}"
        )
        lines.append("")

    lines.append(
        "To book an appointment: call the number listed above directly "
        "and ask for OPD/appointment booking -- this local list doesn't "
        "have online booking links, only live search does."
    )

    return "\n".join(lines)


# ==================================================
# HOSPITAL AGENT
# ==================================================

def run_hospital_agent(
    user_id: str,
    message: str,
    history: list = None,
    memories: list = None,
):

    history = history or []
    memories = memories or []

    location = extract_location(message)
    city = location["city"]
    area = location["area"]

    emergency_only = is_emergency_hospital_request(message)
    booking_requested = is_booking_request(message)
    place_type = guess_place_type(message)

    if not city:
        return {
            "message": (
                "Which city (and area, if you know it) should I search "
                "in? For example: \"hospitals near Andheri, Mumbai\"."
            ),
            "urgency_tier": "urgent" if emergency_only else "normal",
            "agent": "HOSPITAL_AGENT",
            "rag_used": False,
        }

    # ==================================================
    # TRY LIVE DATA FIRST (GOOGLE PLACES)
    # ==================================================

    if is_configured():

        search_terms = [place_type]

        if emergency_only:
            search_terms = ["24 hour emergency hospital"]

        location_text = city if not area else f"{area}, {city}"
        query = f"{' '.join(search_terms)} near {location_text}"

        places = search_medical_places(
            query=query,
            place_type="hospital" if place_type == "hospital" else "doctor",
            limit=6,
        )

        if places:
            response = format_live_places(places, booking_requested)

            return {
                "message": response,
                "urgency_tier": "urgent" if emergency_only else "normal",
                "agent": "HOSPITAL_AGENT",
                "rag_used": False,
                "sources": [
                    {"title": place["name"], "category": "Live search"}
                    for place in places
                ],
            }

        # Configured but genuinely no matches -- say so rather than
        # silently dropping to the (likely thinner) local list.
        return {
            "message": (
                f"I searched live listings near {location_text} but "
                f"couldn't find a match. Try a nearby area, or a "
                f"broader term like just the city name."
            ),
            "urgency_tier": "urgent" if emergency_only else "normal",
            "agent": "HOSPITAL_AGENT",
            "rag_used": False,
        }

    # ==================================================
    # FALLBACK: LOCAL DATABASE
    # ==================================================

    hospitals = search_hospitals(
        city=city,
        area=area,
        emergency_only=emergency_only,
        limit=10,
    )

    if not hospitals:
        location_text = city if not area else f"{city}, {area}"
        return {
            "message": (
                f"I don't have any hospitals listed for {location_text} "
                f"yet. Try just the city name (e.g. \"hospitals in "
                f"{city}\"), a nearby area, or ask your admin to enable "
                f"live search for full, current coverage of every area."
            ),
            "urgency_tier": "urgent" if emergency_only else "normal",
            "agent": "HOSPITAL_AGENT",
            "rag_used": False,
        }

    response = format_local_hospitals(hospitals)

    return {
        "message": response,
        "urgency_tier": "urgent" if emergency_only else "normal",
        "agent": "HOSPITAL_AGENT",
        "rag_used": False,
    }
