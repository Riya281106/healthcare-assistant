# ==================================================
# EMERGENCY DETECTOR  (rewritten)
#
# Safety net that runs BEFORE any AI model. It is rule-based on purpose:
# fast, deterministic, testable, and it works even when the LLM is down.
#
# What changed vs. the old keyword list, and why:
#   * Old negation check looked at only the FIRST occurrence and 4 words back
#     with no clause awareness, so "no fever but chest pain" was treated as a
#     denial and the emergency was MISSED. Now negation is evaluated per
#     clause, per match, and "but/however/,/and" end its reach.
#   * Old text matching was plain substring on lowercase text, so curly
#     apostrophes ("can’t breathe", the phone default) silently missed.
#     Text is now normalised first (clinical_text.normalize).
#   * "stroke" matched "keystroke"/"brushstroke"; matching is now word-bounded
#     with explicit exclusions.
#   * Added: breathing/cardiac/stroke/bleeding/allergy/poisoning variants,
#     Hinglish and Hindi self-harm and symptom phrases.
#   * Returns WHY it fired (category + rule id) so the right first-aid text
#     is shown, and so decisions can be logged without logging the message.
#
# LIMITS (be honest about these): this is pattern matching, not understanding.
# It cannot see a symptom described in unusual words, and it only looks at the
# current message. It is a safety net, not a diagnosis tool.
# ==================================================

from dataclasses import dataclass, field
from typing import List, Optional

from app.utils.clinical_text import split_clauses
from app.utils.red_flag_rules import (
    RULES,
    NEGATION_CUES,
    NEGATION_WINDOW,
    SELF_HARM_NEGATION_WINDOW,
    SCOPE_BREAKERS,
    INFO_QUESTION_START,
    INFO_QUESTION_CONTENT,
    PERSONAL_CUES,
    NEVER_SUPPRESS,
    SELF_HARM,
)

# Order used to pick the "primary" category when several fire at once.
_CATEGORY_PRIORITY = [
    "CARDIAC", "BREATHING", "CHOKING", "ALLERGIC", "STROKE", "EYE", "BLEEDING",
    "CONSCIOUSNESS", "SEIZURE", "POISONING", "SELF_HARM", "GENERAL",
]


@dataclass
class EmergencyAssessment:
    categories: List[str] = field(default_factory=list)
    rule_ids: List[str] = field(default_factory=list)

    @property
    def primary_category(self) -> str:
        for category in _CATEGORY_PRIORITY:
            if category in self.categories:
                return category
        return self.categories[0] if self.categories else "GENERAL"

    @property
    def has_self_harm(self) -> bool:
        return SELF_HARM in self.categories


def _is_negated(clause: str, match_start: int, category: str) -> bool:
    """True if the match is a denial ("no chest pain", "without bleeding")."""
    window = SELF_HARM_NEGATION_WINDOW if category == SELF_HARM else NEGATION_WINDOW

    tokens_before = clause[:match_start].split()

    for token in reversed(tokens_before[-window:]):
        if token in SCOPE_BREAKERS:
            return False
        if token in NEGATION_CUES:
            return True

    return False


def _is_information_question(clause: str) -> bool:
    """
    "What are the symptoms of a stroke?" is a question about a condition,
    not a report of one. Only exempts clearly impersonal questions.
    """
    if not INFO_QUESTION_START.search(clause):
        return False
    if not INFO_QUESTION_CONTENT.search(clause):
        return False
    if PERSONAL_CUES.search(clause):
        return False
    return True


def detect_emergency(message: str) -> Optional[EmergencyAssessment]:
    """Return an assessment if the message reports a red flag, else None."""

    if not message or not message.strip():
        return None

    categories: List[str] = []
    rule_ids: List[str] = []

    for clause in split_clauses(message):

        info_question = _is_information_question(clause)

        for rule_id, category, pattern in RULES:

            for match in pattern.finditer(clause):

                if _is_negated(clause, match.start(), category):
                    continue

                if info_question and category not in NEVER_SUPPRESS:
                    continue

                if category not in categories:
                    categories.append(category)
                if rule_id not in rule_ids:
                    rule_ids.append(rule_id)

                break  # one hit per rule per clause is enough

    if not categories:
        return None

    return EmergencyAssessment(categories=categories, rule_ids=rule_ids)


def is_emergency(message: str) -> bool:
    """Backwards-compatible boolean used by risk_classifier / intent_classifier."""
    return detect_emergency(message) is not None
