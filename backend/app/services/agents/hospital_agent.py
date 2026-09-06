import re

from app.core.database import search_hospitals


# ==================================================
# EXTRACT LOCATION DETAILS
# ==================================================

def extract_location(message: str):

    """
    Extract city and area information
    from the user's hospital-related request.
    """

    message_lower = message.lower()

    city = None
    area = None


    # ==================================================
    # KNOWN CITIES
    # ==================================================

    cities = [
        "mumbai",
        "delhi",
        "pune",
        "bangalore",
        "hyderabad",
        "chennai",
        "kolkata"
    ]

    for known_city in cities:

        if known_city in message_lower:

            city = known_city.title()

            break


    # ==================================================
    # KNOWN AREAS
    # ==================================================

    areas = {
        "andheri": "Andheri",
        "bandra": "Bandra",
        "dadar": "Dadar"
    }

    for key, value in areas.items():

        if key in message_lower:

            area = value

            break


    return {
        "city": city,
        "area": area
    }


# ==================================================
# CHECK EMERGENCY REQUEST
# ==================================================

def is_emergency_hospital_request(message: str):

    message_lower = message.lower()

    emergency_keywords = [

        "emergency hospital",
        "emergency",
        "urgent hospital",
        "24 hour hospital",
        "24-hour hospital",
        "emergency care"

    ]

    for keyword in emergency_keywords:

        if keyword in message_lower:

            return True

    return False


# ==================================================
# FORMAT HOSPITAL RESULTS
# ==================================================

def format_hospitals(hospitals):

    if not hospitals:

        return None


    response = "Here are the hospitals I found:\n\n"


    for hospital in hospitals:

        response += f"• {hospital['name']}\n"

        if hospital["area"]:

            response += f"  Area: {hospital['area']}\n"

        if hospital["address"]:

            response += f"  Address: {hospital['address']}\n"

        if hospital["phone"]:

            response += f"  Phone: {hospital['phone']}\n"

        response += (
            f"  Emergency Available: "
            f"{hospital['emergency_available']}\n\n"
        )


    return response


# ==================================================
# HOSPITAL AGENT
# ==================================================

def run_hospital_agent(
    user_id: str,
    message: str,
    history: list = None,
    memories: list = None
):

    history = history or []
    memories = memories or []


    # ==================================================
    # EXTRACT LOCATION
    # ==================================================

    location = extract_location(message)

    city = location["city"]

    area = location["area"]


    # ==================================================
    # CHECK EMERGENCY REQUIREMENT
    # ==================================================

    emergency_only = is_emergency_hospital_request(
        message
    )


    # ==================================================
    # SEARCH DATABASE
    # ==================================================

    hospitals = search_hospitals(

        city=city,

        area=area,

        emergency_only=emergency_only,

        limit=10
    )


    # ==================================================
    # NO HOSPITAL FOUND
    # ==================================================

    if not hospitals:

        if city:

            location_text = city

            if area:

                location_text += f", {area}"

            return {
                "message": (
                    f"I could not find any hospitals in "
                    f"{location_text} in the current hospital database."
                ),

                "urgency_tier": (
                    "urgent"
                    if emergency_only
                    else "normal"
                ),

                "agent": "HOSPITAL_AGENT",

                "rag_used": False
            }


        return {
            "message": (
                "Please specify your city or area so I can "
                "search the hospital database more accurately."
            ),

            "urgency_tier": "normal",

            "agent": "HOSPITAL_AGENT",

            "rag_used": False
        }


    # ==================================================
    # FORMAT RESULTS
    # ==================================================

    response = format_hospitals(
        hospitals
    )


    # ==================================================
    # EMERGENCY MESSAGE
    # ==================================================

    if emergency_only:

        response = (
            "Emergency hospitals matching your request:\n\n"
            + response.replace(
                "Here are the hospitals I found:\n\n",
                ""
            )
        )


    # ==================================================
    # RETURN RESPONSE
    # ==================================================

    return {

        "message": response,

        "urgency_tier": (
            "urgent"
            if emergency_only
            else "normal"
        ),

        "agent": "HOSPITAL_AGENT",

        "rag_used": False
    }