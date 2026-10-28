import os

from app.services.rag.vector_store import search_documents
from app.utils.language import detect_language


# A distance above this is treated as "not actually relevant" and
# filtered out rather than forced into the prompt. Chroma's default
# embedding function uses squared-L2 distance, where lower is closer;
# this cutoff was picked empirically against the curated knowledge
# base topics -- it can be tuned as the knowledge base grows.
# Measured on this project's own knowledge base (28 Oct 2026): English questions the
# base covers scored 0.55-0.92, English questions it does NOT cover scored 1.1-1.55.
# 1.6 let wrong matches through (e.g. a drug-dose question matched the generic
# pain-medicine page), so the default is now 1.0. Tune with RAG_DISTANCE_CUTOFF in .env
# after re-running calibrate.py. Lower = stricter = more "I don't have that" answers.
RELEVANCE_DISTANCE_CUTOFF = float(os.getenv("RAG_DISTANCE_CUTOFF", "1.0"))


_TRANSLATE_PROMPT = (
    "Translate the user's message into short, plain English for a medical knowledge-base "
    "search. Output ONLY the English text. Do not answer it, explain it, or add anything."
)


def to_english_for_search(query: str) -> str:
    """
    The embedding model is English-focused: Hindi / Marathi questions found nothing
    at all in calibration, Hinglish matched weakly. So non-English queries are
    translated to English first (one short LLM call). If that fails for any reason
    the original query is used, so retrieval never breaks because of translation.
    Only the SEARCH query is translated; the user's message and the reply language
    are untouched.
    """

    if detect_language(query) == "en":
        return query

    try:
        from app.services.llm.client import generate

        translated = (generate([{"role": "user", "content": query}], _TRANSLATE_PROMPT) or "").strip()
    except Exception:
        return query

    if not translated or len(translated) > 300:
        return query

    return translated


def retrieve(query: str, top_k: int = 3):
    """
    Run the retrieval pipeline: embed the query, run similarity
    search, and filter out weak matches.

    Returns a list of structured chunk dicts:
        {
            "text": ...,
            "source": ...,
            "title": ...,
            "category": ...,
            "section": ...,
            "chunk_id": ...,
            "distance": ...,
            "relevance_score": 0..1 (higher = more relevant)
        }
    """

    query = (query or "").strip()

    if not query:
        return []

    raw_results = search_documents(to_english_for_search(query), top_k=top_k)

    retrieved = []

    for result in raw_results:

        document = result.get("document", "")
        distance = result.get("distance")

        if not document:
            continue

        if distance is not None and distance > RELEVANCE_DISTANCE_CUTOFF:
            continue

        metadata = result.get("metadata", {}) or {}

        relevance_score = None
        if distance is not None:
            relevance_score = round(max(0.0, 1 - (distance / (RELEVANCE_DISTANCE_CUTOFF * 2))), 3)

        retrieved.append({
            "text": document,
            "source": metadata.get("source", "unknown"),
            "title": metadata.get("title", metadata.get("source", "Knowledge base")),
            "category": metadata.get("category", "General"),
            "section": metadata.get("section", "General"),
            "chunk_id": result.get("chunk_id"),
            "distance": distance,
            "relevance_score": relevance_score
        })

    return retrieved


def build_context_and_sources(chunks: list):
    """
    Turn retrieved chunks into:
      - a citation-annotated context block to feed the LLM, e.g.
        "[1] Understanding Fever in Adults - Self-Care Measures\n<text>"
      - a de-duplicated, UI-safe list of sources actually used,
        e.g. [{"title": "...", "category": "...", "section": "..."}]

    De-duplicates by (title, section) so citing two chunks from the
    same section doesn't show the same source card twice.
    """

    if not chunks:
        return "", []

    context_parts = []
    sources = []
    seen = set()

    citation_number = 0

    for chunk in chunks:

        key = (chunk["title"], chunk["section"])

        if key not in seen:
            citation_number += 1
            seen.add(key)

            sources.append({
                "title": chunk["title"],
                "category": chunk["category"],
                "section": chunk["section"],
                "relevance_score": chunk["relevance_score"]
            })

        context_parts.append(
            f"[{citation_number}] {chunk['title']} - {chunk['section']}\n{chunk['text']}"
        )

    context_block = "\n\n".join(context_parts)

    return context_block, sources


def retrieve_medical_context(query: str, top_k: int = 3):
    """
    Backward-compatible helper used by agents: returns
    (context_text_for_prompt, sources_list_for_ui).
    """

    chunks = retrieve(query, top_k=top_k)

    return build_context_and_sources(chunks)
