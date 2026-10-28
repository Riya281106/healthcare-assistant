"""
Text normalisation + clause splitting for safety checks.

Why this exists: people type on phones. "can’t breathe" (curly apostrophe),
"CANT BREATHE", "can  not   breathe" and "can't breathe" must all look the
same to the emergency detector. The old detector only matched the plain
ASCII apostrophe, so curly-apostrophe messages (the default on iOS/Android
keyboards) silently missed.
"""

import re
import unicodedata

# Every apostrophe-like character we want to drop ("can't" -> "cant").
_APOSTROPHES = "'\u2019\u2018\u02bc\u02b9\u0060\u00b4\u2032"

# Words that end a negation's reach: "no fever BUT chest pain".
_CLAUSE_BREAK_WORDS = (
    "but", "however", "although", "though", "except", "yet", "while", "whereas",
)

# Sentence-level separators (kept as hard breaks BEFORE we strip punctuation).
_SENTENCE_SPLIT = re.compile(r"[.!?;:\n\r\u0964]+")  # \u0964 = Devanagari danda
_BREAK_WORD_SPLIT = re.compile(
    r"\b(?:" + "|".join(_CLAUSE_BREAK_WORDS) + r")\b", re.IGNORECASE
)


def _clean(text: str) -> str:
    """Lowercase, drop apostrophes, replace punctuation/symbols with spaces."""
    text = unicodedata.normalize("NFKC", text).lower()

    for ch in _APOSTROPHES:
        text = text.replace(ch, "")

    out = []
    for ch in text:
        category = unicodedata.category(ch)
        # Keep letters, combining marks (Devanagari vowel signs!) and digits.
        if category[0] in ("L", "M", "N"):
            out.append(ch)
        elif ch == ",":
            out.append(" , ")  # keep commas: they matter for negation scope
        else:
            out.append(" ")

    return re.sub(r"\s+", " ", "".join(out)).strip()


def normalize(text: str) -> str:
    """Single normalised string (no clause structure)."""
    if not text:
        return ""
    return _clean(text)


def split_clauses(text: str) -> list:
    """
    Split a message into clauses, each normalised.

    Breaks on sentence punctuation and on contrast words (but/however/...),
    so a negation in one clause never leaks into the next.
    Commas are kept inside a clause as ',' tokens.
    """
    if not text:
        return []

    clauses = []
    for sentence in _SENTENCE_SPLIT.split(text):
        for part in _BREAK_WORD_SPLIT.split(sentence):
            cleaned = _clean(part)
            if cleaned:
                clauses.append(cleaned)
    return clauses
