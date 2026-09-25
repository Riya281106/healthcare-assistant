import os
import chromadb


# ---------------------------------------------------------
# ChromaDB storage location
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

CHROMA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "chroma"
)


# ---------------------------------------------------------
# Create persistent ChromaDB client
# ---------------------------------------------------------

os.makedirs(CHROMA_PATH, exist_ok=True)

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)


# ---------------------------------------------------------
# Medical knowledge collection
# ---------------------------------------------------------

collection = client.get_or_create_collection(
    name="medical_knowledge"
)


# ---------------------------------------------------------
# Add a document/chunk to the knowledge base
# ---------------------------------------------------------

def add_document(
    document_id: str,
    text: str,
    metadata: dict | None = None
):

    if not text or not text.strip():
        raise ValueError(
            "Document text cannot be empty."
        )

    collection.upsert(
        ids=[document_id],
        documents=[text],
        metadatas=[metadata or {}]
    )


def add_documents_batch(
    document_ids: list,
    texts: list,
    metadatas: list
):
    """Upsert many chunks in a single call (used by the ingestion pipeline)."""

    if not document_ids:
        return

    collection.upsert(
        ids=document_ids,
        documents=texts,
        metadatas=metadatas
    )


# ---------------------------------------------------------
# Search medical knowledge
# ---------------------------------------------------------

def search_documents(
    query: str,
    top_k: int = 3
):

    if not query or not query.strip():
        return []

    # Guard against asking for more results than exist -- Chroma
    # raises if n_results > the number of stored items.
    available = get_document_count()

    if available == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, available)
    )

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    ids = results.get(
        "ids",
        [[]]
    )[0]

    retrieved = []

    for index, document in enumerate(documents):

        retrieved.append({
            "chunk_id": (
                ids[index]
                if index < len(ids)
                else None
            ),

            "document": document,

            "metadata": (
                metadatas[index]
                if index < len(metadatas)
                else {}
            ),

            "distance": (
                distances[index]
                if index < len(distances)
                else None
            )
        })

    return retrieved


# ---------------------------------------------------------
# Get number of stored chunks
# ---------------------------------------------------------

def get_document_count():

    return collection.count()


# ---------------------------------------------------------
# Delete every chunk that came from a given source file.
# Used by the ingestion pipeline to re-index a changed file
# without leaving stale chunks behind.
# ---------------------------------------------------------

def delete_by_source(source: str):

    try:
        collection.delete(
            where={"source": source}
        )
    except Exception:
        # Nothing to delete yet (e.g. first-time ingestion) -- safe to ignore.
        pass


# ---------------------------------------------------------
# Aggregate stats: distinct source documents, chunk counts,
# categories. Powers the Knowledge / Sources page.
# ---------------------------------------------------------

def get_source_stats():

    if get_document_count() == 0:
        return []

    everything = collection.get(
        include=["metadatas"]
    )

    metadatas = everything.get("metadatas", []) or []

    by_source = {}

    for meta in metadatas:

        source = meta.get("source", "unknown")

        if source not in by_source:
            by_source[source] = {
                "source": source,
                "title": meta.get("title", source),
                "category": meta.get("category", "General"),
                "doc_type": meta.get("doc_type", "patient_education"),
                "last_updated": meta.get("last_updated"),
                "chunk_count": 0
            }

        by_source[source]["chunk_count"] += 1

    return sorted(
        by_source.values(),
        key=lambda item: item["title"]
    )


# ---------------------------------------------------------
# Clear entire medical knowledge collection
# ---------------------------------------------------------

def clear_collection():

    global collection

    # Delete the existing collection
    try:
        client.delete_collection(
            name="medical_knowledge"
        )
    except Exception:
        pass

    # Create a completely fresh collection
    collection = client.get_or_create_collection(
        name="medical_knowledge"
    )

    print(
        "ChromaDB medical knowledge collection cleared."
    )
