"""
Language detection, language switching and the "reply in this language" hint.

Deliberately rule-based (no model call): it is instant, free, deterministic and
testable, and it never delays an emergency reply.

Codes used everywhere in the app:
    en        English
    hi        Hindi (Devanagari)
    mr        Marathi (Devanagari)
    hinglish  Hindi written in Roman letters, mixed with English
    ta/te/bn/gu/kn/ml/pa   detected from script only; the LLM is asked to reply
                           in that language (quality depends on the model)

LIMITS: Hindi vs Marathi in Devanagari is decided by marker words; a very short
message ("dard hai") can be mis-detected. The user can always override with the
language selector or by saying "reply in Marathi".
"""

import re
from contextvars import ContextVar
from typing import Optional, Tuple

SUPPORTED_CORE = ("en", "hi", "mr", "hinglish")

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "hinglish": "Hinglish",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
}

# Unicode blocks for scripts that identify a language on their own.
_SCRIPT_RANGES = [
    ("bn", 0x0980, 0x09FF),
    ("pa", 0x0A00, 0x0A7F),
    ("gu", 0x0A80, 0x0AFF),
    ("ta", 0x0B80, 0x0BFF),
    ("te", 0x0C00, 0x0C7F),
    ("kn", 0x0C80, 0x0CFF),
    ("ml", 0x0D00, 0x0D7F),
]

_MARATHI_MARKERS = {
    "आहे", "आहेत", "मला", "माझ", "माझा", "माझी", "माझे", "तुम्ही", "तुम्हाला", "काय",
    "करा", "होत", "होतो", "होते", "झाल", "झाला", "झाली", "डोळ", "डोळा", "डोळ्यात",
    "दुखत", "दुखतंय", "आणि", "पाहिजे", "द्या", "मध्ये", "सांगा", "नको", "कुठे",
    "रुग्णालय", "मराठी", "मराठीत", "आम्ही", "त्याला", "तिला", "होय", "नाही",
}
_HINDI_MARKERS = {
    "है", "हैं", "मुझे", "मेरी", "मेरा", "मेरे", "क्या", "आप", "और", "में", "नहीं",
    "रहा", "रही", "रहे", "कृपया", "हूँ", "हूं", "था", "थी", "कैसे", "क्यों", "बताओ",
    "बताइए", "हिंदी", "हिन्दी", "अस्पताल", "दर्द", "चाहिए", "करो", "कर", "के", "का", "की",
}
# "नाही" is Marathi, "नहीं" is Hindi; "नाही" is in the Marathi set above.

_HINGLISH_TOKENS = {
    "mera", "meri", "mere", "mujhe", "mujhko", "hai", "hain", "hoon", "hu", "nahi", "nahin",
    "nhi", "kya", "kyun", "kyu", "kaise", "kaisa", "kab", "kahan", "aankh", "ankh", "dard",
    "raha", "rahi", "rahe", "ho", "hua", "hui", "bukhar", "sar", "pet", "seene", "mein",
    "me", "se", "ko", "ka", "ki", "ke", "aur", "bhi", "batao", "bataiye", "karo", "kar",
    "chahiye", "dikhao", "dhundo", "paas", "pass", "wala", "wali", "thoda", "bahut", "bohot",
    "zyada", "kam", "abhi", "achanak", "dawai", "dawa", "doctor", "aap", "tum", "main",
    "rehta", "rahta", "rehti", "rahti", "haan", "han", "theek", "thik", "samjhao", "bolo",
}
_MARATHI_ROMAN_TOKENS = {
    "mala", "maza", "majha", "mazi", "majhi", "aahe", "ahe", "aahet", "dukhat", "dukhtay",
    "kay", "tumhi", "pahije", "madhe", "sanga", "kuthe", "ahet", "zala", "zali", "hoto",
    "hote", "nako", "hoy", "tumhala", "amhi",
}

# --- explicit "switch language" requests ------------------------------------
_LANG_WORDS = {
    "hi": r"hindi|हिंदी|हिन्दी",
    "mr": r"marathi|मराठी",
    "en": r"english|angrezi|inglish|अंग्रेजी|अंग्रेज़ी|इंग्रजी",
    "hinglish": r"hinglish",
}


def _switch_patterns(words: str):
    return [
        re.compile(rf"\b(?:in|into|to|use|switch to|change to|speak|reply in|respond in|answer in)\s+(?:{words})\b", re.I),
        re.compile(rf"(?:{words})\s*(?:mein|me|main|madhe|में|मे|मध्ये|मधे|please|plz|pls|bolo|batao|samjhao|bol|sang|sanga)\b", re.I),
        re.compile(rf"(?:{words})(?:त|मध्ये|में|मे)\b", re.I),  # मराठीत
        re.compile(rf"(?:{words})\s*(?:में|मे|मध्ये|त)?\s*(?:बताओ|बताइए|समझाओ|समझाइए|बोलो|सांगा|सांग|समजावा)", re.I),
    ]


_SWITCH_RE = {code: _switch_patterns(words) for code, words in _LANG_WORDS.items()}

_WORD_RE = re.compile(r"[a-zA-Z']+")
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def detect_language(message: str) -> str:
    """Best-guess language code for one message. Never raises."""
    text = message or ""
    letters = _LETTER.findall(text)
    if not letters:
        return "en"

    # Non-Devanagari Indian scripts identify themselves.
    for code, lo, hi_ in _SCRIPT_RANGES:
        if sum(1 for ch in text if lo <= ord(ch) <= hi_) >= max(2, len(letters) * 0.3):
            return code

    deva = len(_DEVANAGARI.findall(text))
    if deva >= max(2, len(letters) * 0.3):
        tokens = set(re.findall(r"[\u0900-\u097F]+", text))
        mr = sum(1 for t in tokens if t in _MARATHI_MARKERS or any(t.startswith(m) for m in ("माझ", "डोळ", "दुखत", "झाल")))
        hi = sum(1 for t in tokens if t in _HINDI_MARKERS)
        if mr > hi:
            return "mr"
        return "hi"

    tokens = [t.lower() for t in _WORD_RE.findall(text)]
    mr_hits = sum(1 for t in tokens if t in _MARATHI_ROMAN_TOKENS)
    hg_hits = sum(1 for t in tokens if t in _HINGLISH_TOKENS)
    if mr_hits >= 2 and mr_hits >= hg_hits - 1:
        return "mr"
    if hg_hits >= 2:
        return "hinglish"
    return "en"


def detect_language_switch(message: str) -> Optional[str]:
    """If the user explicitly asks for another language, return its code."""
    text = message or ""
    for code, patterns in _SWITCH_RE.items():
        if any(p.search(text) for p in patterns):
            return code
    return None


def normalize_ui_language(value: Optional[str]) -> Optional[str]:
    """Language chosen in the selector: a known code, or None for 'auto'."""
    if not value:
        return None
    value = value.strip().lower()
    if value in ("auto", ""):
        return None
    return value if value in LANGUAGE_NAMES else None


def resolve_language(
    message: str,
    ui_language: Optional[str] = None,
    stored: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Decide the reply language.

    Priority: explicit request in the message > selector > stored preference
    > detected language of this message.

    Returns (language_to_use, preference_to_store_or_None). A preference is
    stored only when the user explicitly chose one, so plain detection never
    "locks" a language.
    """
    switched = detect_language_switch(message)
    if switched:
        return switched, switched

    chosen = normalize_ui_language(ui_language)
    if chosen:
        return chosen, chosen

    if stored and stored in LANGUAGE_NAMES:
        return stored, None

    return detect_language(message), None


_FORMAT_RULES = (
    " Write plain text only: no markdown symbols such as ** or ## or backticks."
    " Keep it short and clear, use simple everyday words, explain any medical"
    " term in plain language, and do not repeat advice already given."
)


def language_instruction(code: Optional[str]) -> str:
    """Sentence appended to LLM prompts so the answer comes back in `code`."""
    if not code or code == "en":
        return "Reply in simple English." + _FORMAT_RULES
    if code == "hi":
        return "Reply in Hindi (Devanagari script) using simple everyday words." + _FORMAT_RULES
    if code == "mr":
        return "Reply in Marathi (Devanagari script) using simple everyday words." + _FORMAT_RULES
    if code == "hinglish":
        return (
            "Reply in Hinglish: Hindi written in Roman letters, mixed naturally with common "
            "English medical words, the way the user writes." + _FORMAT_RULES
        )
    name = LANGUAGE_NAMES.get(code, "the user's language")
    return f"Reply in {name}, using simple everyday words." + _FORMAT_RULES


# The orchestrator sets this once per request; the LLM call sites read it.
_reply_language: ContextVar[Optional[str]] = ContextVar("reply_language", default=None)


def set_reply_language(code: Optional[str]):
    return _reply_language.set(code)


def get_reply_language() -> Optional[str]:
    return _reply_language.get()


# True when the reply language is a lasting choice (selector, "reply in Marathi",
# or a saved preference), so the UI can show it instead of "Auto".
_language_pinned: ContextVar[bool] = ContextVar("language_pinned", default=False)


def set_language_pinned(value: bool):
    return _language_pinned.set(value)


def get_language_pinned() -> bool:
    return _language_pinned.get()
