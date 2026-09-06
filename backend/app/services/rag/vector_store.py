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


# ---------------------------------------------------------
# Search medical knowledge
# ---------------------------------------------------------

def search_documents(
    query: str,
    top_k: int = 3
):

    if not query or not query.strip():
        return []

    results = collection.query(
        query_texts=[query],
        n_results=top_k
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

    retrieved = []

    for index, document in enumerate(documents):

        retrieved.append({
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
# Get number of stored documents
# ---------------------------------------------------------

def get_document_count():

    return collection.count()


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