import os

KNOWLEDGE_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "knowledge_base"
)

def fix_mojibake(text):
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text

for filename in sorted(os.listdir(KNOWLEDGE_BASE_DIR)):
    if not filename.lower().endswith(".txt"):
        continue

    file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)

    with open(file_path, "r", encoding="utf-8") as f:
        original = f.read()

    fixed = fix_mojibake(original)

    if fixed != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed)
        print("Fixed encoding: " + filename)
    else:
        print("No change needed: " + filename)
