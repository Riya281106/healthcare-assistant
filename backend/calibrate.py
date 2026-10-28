"""
Prints, for each question, the closest knowledge-base distance (lower = better match).
Run:  python calibrate.py     (from the backend folder, venv active)
Needs GROQ_API_KEY in .env for non-English questions (they are translated first).
"""
from app.services.rag.retriever import to_english_for_search
from app.services.rag.vector_store import search_documents

GOOD = [  # topics the knowledge base covers
    "What is hypertension?", "how to lower high blood pressure",
    "fever kya hota hai", "bukhar mein kya karein",
    "What is diabetes?", "sugar ki bimari kya hai",
    "headache home remedies", "sar dard ke liye kya karein",
    "how to treat a minor cut", "सर्दी जुकाम में क्या करें",
    "ताप म्हणजे काय", "tips for better sleep",
]
BAD = [  # not covered
    "dose of drug XYZ for rare disease Q", "how to treat a snake bite",
    "what is the treatment for cancer", "best football team in the world",
]


def best(q):
    english = to_english_for_search(q)
    results = search_documents(english, top_k=3)
    distances = [r["distance"] for r in results if r.get("distance") is not None]
    return (round(min(distances), 2) if distances else None), english


def show(title, questions):
    print(title)
    for q in questions:
        d, english = best(q)
        note = "" if english == q else f"   [searched as: {english}]"
        print(f"  {d}  {q}{note}")


show("COVERED topics (want LOW numbers):", GOOD)
show("NOT covered (want HIGH numbers):", BAD)
print("\nPick RAG_DISTANCE_CUTOFF between the highest COVERED number and the lowest NOT-covered number.")
