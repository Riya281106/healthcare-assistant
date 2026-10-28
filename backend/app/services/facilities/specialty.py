"""
Maps what the user says (English / Hinglish / Hindi / Marathi) to a medical
specialty and a search phrase for the places search.

This only chooses WHAT KIND of facility to look for. It is not a diagnosis.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Specialty:
    key: str
    label: str          # shown to the user (English; facility data is English)
    search_term: str    # used in the places query
    place_type: str     # "hospital" or "doctor"


SPECIALTIES = {
    "eye": Specialty("eye", "Ophthalmology / Eye care", "eye hospital", "hospital"),
    "dental": Specialty("dental", "Dentistry", "dental clinic", "doctor"),
    "skin": Specialty("skin", "Dermatology / Skin care", "skin specialist dermatologist clinic", "doctor"),
    "ent": Specialty("ent", "ENT (ear, nose, throat)", "ENT specialist hospital", "doctor"),
    "heart": Specialty("heart", "Cardiology / Heart care", "cardiology hospital", "hospital"),
    "ortho": Specialty("ortho", "Orthopaedics / Bone and joint", "orthopedic hospital", "hospital"),
    "child": Specialty("child", "Paediatrics / Child care", "children hospital pediatrician", "hospital"),
    "women": Specialty("women", "Gynaecology / Women's health", "gynecologist maternity hospital", "hospital"),
    "general": Specialty("general", "General hospital", "hospital", "hospital"),
}

_KEYWORDS = [
    ("eye", r"\b(?:eye|eyes|ophthalm\w*|vision|aankh|aankhon|ankh|aankho|doka|dola|netra)\b|आँख|आंख|आँखों|डोळ|नेत्र"),
    ("dental", r"\b(?:dental|dentist|tooth|teeth|daant|dant|daat)\b|दांत|दाँत|दात"),
    ("skin", r"\b(?:skin|dermat\w*|rash|twacha|tvacha)\b|त्वचा|त्वचेच"),
    ("ent", r"\b(?:ent|ear|ears|nose|throat|kaan|naak|gala|kan)\b|कान|नाक|गला|घसा"),
    ("heart", r"\b(?:heart|cardio\w*|dil)\b|हृदय|दिल"),
    ("ortho", r"\b(?:bone|bones|joint|joints|ortho\w*|fracture|haddi)\b|हड्डी|हाड"),
    ("child", r"\b(?:child|children|kid|kids|baby|paediatric\w*|pediatric\w*|bachcha|bachche)\b|बच्चा|बच्चे|मूल"),
    ("women", r"\b(?:gynae\w*|gynec\w*|maternity|pregnan\w*|women)\b|गर्भ|प्रसूति"),
]

_COMPILED = [(key, re.compile(pat, re.IGNORECASE)) for key, pat in _KEYWORDS]


def detect_specialty(text: str) -> Optional[Specialty]:
    """First matching specialty, or None if the text names none."""
    for key, pattern in _COMPILED:
        if pattern.search(text or ""):
            return SPECIALTIES[key]
    return None


def specialty_by_key(key: Optional[str]) -> Optional[Specialty]:
    return SPECIALTIES.get(key) if key else None
