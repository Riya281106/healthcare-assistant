from app.services.rag.vector_store import search_documents


def retrieve_medical_context(
    query: str,
    top_k: int = 3
) -> str:

    results = search_documents(
        query,
        top_k=top_k
    )

    if not results:
        return ""

    context_parts = []

    for result in results:

        document = result.get("document", "")

        if document:
            context_parts.append(document)

    return "\n\n".join(context_parts)