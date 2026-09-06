import os

from app.services.rag.vector_store import (
    add_document,
    get_document_count,
    clear_collection
)

# ---------------------------------------------------------
# Locate knowledge base
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

KNOWLEDGE_BASE_DIR = os.path.join(
    BASE_DIR,
    "knowledge_base"
)


# ---------------------------------------------------------
# RAG CHUNKING SETTINGS
# ---------------------------------------------------------

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


# ---------------------------------------------------------
# Split medical document into smaller chunks
# ---------------------------------------------------------

def chunk_text(text: str):

    sections = []
    current_section = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Medical section headings
        if line.upper() in {
            "HEADACHE",
            "FEVER",
            "PARACETAMOL",
            "HYPERTENSION"
        }:

            if current_section:
                sections.append(
                    "\n".join(current_section)
                )

            current_section = [line]

        else:

            current_section.append(line)

    # Add final section
    if current_section:
        sections.append(
            "\n".join(current_section)
        )

    return sections

# ---------------------------------------------------------
# Load text files into ChromaDB
# ---------------------------------------------------------

def load_knowledge_base():

    if not os.path.exists(KNOWLEDGE_BASE_DIR):

        raise FileNotFoundError(
            f"Knowledge base not found: {KNOWLEDGE_BASE_DIR}"
        )

    files_loaded = 0
    chunks_loaded = 0

    for filename in os.listdir(KNOWLEDGE_BASE_DIR):

        if not filename.lower().endswith(".txt"):
            continue

        file_path = os.path.join(
            KNOWLEDGE_BASE_DIR,
            filename
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            text = file.read()

        if not text.strip():
            continue

        # -------------------------------------------------
        # Split document into smaller chunks
        # -------------------------------------------------

        chunks = chunk_text(text)

        print(
            f"\nProcessing: {filename}"
        )

        print(
            f"Chunks created: {len(chunks)}"
        )

        # -------------------------------------------------
        # Store every chunk separately
        # -------------------------------------------------

        for index, chunk in enumerate(chunks):

            document_id = f"{filename}_chunk_{index}"

            add_document(
                document_id=document_id,
                text=chunk,
                metadata={
                    "source": filename,
                    "type": "medical_knowledge",
                    "chunk_index": index
                }
            )

            chunks_loaded += 1

        files_loaded += 1

    print(
        f"\nTotal files processed: {files_loaded}"
    )

    print(
        f"Total chunks added: {chunks_loaded}"
    )

    return files_loaded


# ---------------------------------------------------------
# Run loader
# ---------------------------------------------------------

if __name__ == "__main__":

    clear_collection()

    count = load_knowledge_base()

    print(
        f"\nKnowledge-base files processed: {count}"
    )

    print(
        f"Total documents in ChromaDB: "
        f"{get_document_count()}"
    )