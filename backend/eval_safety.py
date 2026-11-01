"""
Measured safety check for the emergency detector.   Run:  python eval_safety.py

Prints, on the fixed labelled list in tests/safety_cases.py:
  * recall      = real emergencies detected / all real emergencies
  * false alarms = harmless messages that wrongly fired
  * category accuracy for the emergencies it caught
and lists every miss. Quote these numbers (with the size of the list) in the report;
they are NOT a guarantee for phrasings that are not on the list.
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "x" * 40)
os.environ.setdefault("GROQ_API_KEY", "eval")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))

from app.utils.emergency_detector import detect_emergency  # noqa: E402
from safety_cases import BENIGN, EMERGENCY  # noqa: E402


def main() -> int:
    missed, wrong_cat, caught = [], [], 0
    for text, expected in EMERGENCY:
        found = detect_emergency(text)
        if found is None:
            missed.append(text)
        else:
            caught += 1
            if expected not in found.categories:
                wrong_cat.append((text, expected, found.categories))

    false_alarms = [t for t in BENIGN if detect_emergency(t) is not None]

    total_e, total_b = len(EMERGENCY), len(BENIGN)
    print(f"Real emergencies on the list : {total_e}")
    print(f"  detected                   : {caught}  (recall {100 * caught / total_e:.1f}%)")
    print(f"  missed                     : {len(missed)}")
    print(f"  right category             : {caught - len(wrong_cat)} of {caught}")
    print(f"Harmless messages on the list: {total_b}")
    print(f"  false alarms               : {len(false_alarms)}  ({100 * len(false_alarms) / total_b:.1f}%)")
    for t in missed:
        print("  MISSED     :", t)
    for t, exp, got in wrong_cat:
        print(f"  WRONG TYPE : {t}  (expected {exp}, got {got})")
    for t in false_alarms:
        print("  FALSE ALARM:", t)
    return 1 if (missed or false_alarms) else 0


if __name__ == "__main__":
    sys.exit(main())
