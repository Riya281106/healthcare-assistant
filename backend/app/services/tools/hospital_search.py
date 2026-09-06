# app/services/tools/hospital_search.py


def search_hospitals(location: str) -> list:
    """
    Search for hospitals based on city/location.

    This is a simple local hospital-search tool
    used by the Hospital Agent.
    """

    hospitals = {
        "mumbai": [
            {
                "name": "Sir J.J. Hospital",
                "area": "Byculla, Mumbai"
            },
            {
                "name": "Kokilaben Dhirubhai Ambani Hospital",
                "area": "Andheri, Mumbai"
            },
            {
                "name": "Lilavati Hospital",
                "area": "Bandra, Mumbai"
            }
        ],

        "pune": [
            {
                "name": "Ruby Hall Clinic",
                "area": "Sassoon Road, Pune"
            },
            {
                "name": "Jehangir Hospital",
                "area": "Sangamvadi, Pune"
            }
        ],

        "kolkata": [
            {
                "name": "Apollo Multispecialty Hospitals",
                "area": "Kolkata"
            },
            {
                "name": "AMRI Hospitals",
                "area": "Kolkata"
            },
            {
                "name": "Fortis Hospital",
                "area": "Anandapur, Kolkata"
            }
        ]
    }

    location = location.lower().strip()

    return hospitals.get(location, [])