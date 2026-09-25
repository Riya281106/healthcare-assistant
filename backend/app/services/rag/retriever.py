from app.services.rag.vector_store import search_documents


# A distance above this is treated as "not actually relevant" and
# filtered out rather than forced into the prompt. Chroma's default
# embedding function uses squared-L2 distance, where lower is closer;
# this cutoff was picked empirically against the curated knowledge
# base topics -- it can be tuned as the knowledge base grows.
RELEVANCE_DISTANCE_CUTOFF = 1.6


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

    raw_results = search_documents(query, top_k=top_k)

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
