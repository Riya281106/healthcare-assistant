"""
Maharashtra-only scope for hospital search.

The assistant is deliberately limited to Maharashtra so every result can be checked against
a known area. Two checks:

  1. PIN codes: Maharashtra's postal range is 400xxx to 445xxx. (Goa is 403xxx, so 403 is
     excluded; Gujarat, Karnataka, Madhya Pradesh and Telangana use other prefixes.)
  2. Coordinates from the geocoder must fall inside Maharashtra's state boundary box
     (checked in osm_places) and, when the geocoder reports a state, it must be Maharashtra.

These are first-three-digit prefixes of PIN codes that exist in Maharashtra.
"""

import re
from typing import Optional

MH_PIN_PREFIXES = frozenset({
    "400", "401", "402",                      # Mumbai, Thane, Palghar, Raigad (part)
    "410", "411", "412",                      # Raigad, Pune
    "413", "414", "415", "416",               # Solapur/Latur/Osmanabad, Ahmednagar, Satara/Sangli/Ratnagiri, Kolhapur/Sindhudurg
    "421", "422", "423", "424", "425",        # Thane (Kalyan), Nashik, Dhule, Jalgaon
    "431",                                    # Chhatrapati Sambhajinagar, Jalna, Beed, Nanded, Parbhani, Hingoli
    "440", "441", "442", "443", "444", "445", # Nagpur, Wardha, Chandrapur, Gadchiroli, Buldhana, Akola, Amravati, Yavatmal
})

# Maharashtra's rough bounding box (south, north, west, east).
MH_BBOX = (15.60, 22.10, 72.60, 80.95)

_PIN = re.compile(r"^[1-9]\d{5}$")


def is_maharashtra_pin(pin: Optional[str]) -> bool:
    pin = (pin or "").strip()
    return bool(_PIN.match(pin)) and pin[:3] in MH_PIN_PREFIXES


def in_maharashtra_box(lat: float, lon: float) -> bool:
    south, north, west, east = MH_BBOX
    return south <= lat <= north and west <= lon <= east


OUTSIDE_MESSAGE = (
    "I can only search for hospitals and clinics in Maharashtra right now, and that "
    "doesn't look like a Maharashtra location. Please share a Maharashtra PIN code "
    "(they start with 40 to 44, for example 400001 or 411001) or an area and city in "
    "Maharashtra, such as Andheri, Mumbai or Kothrud, Pune."
)
