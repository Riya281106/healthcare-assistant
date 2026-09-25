import os
import re
import json
import hashlib

from app.services.rag.vector_store import (
    add_documents_batch,
    delete_by_source,
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

# Manifest tracks a hash of each source file's content so re-indexing
# only re-embeds files that actually changed, and reports what changed.
MANIFEST_PATH = os.path.join(
    BASE_DIR,
    "data",
    "kb_manifest.json"
)


# ---------------------------------------------------------
# RAG CHUNKING SETTINGS
# ---------------------------------------------------------

CHUNK_SIZE = 700       # target characters per chunk
CHUNK_OVERLAP = 120    # characters of overlap between adjacent chunks


# ---------------------------------------------------------
# Manifest helpers (change detection for re-indexing)
# ---------------------------------------------------------

def _load_manifest():

    if not os.path.exists(MANIFEST_PATH):
        return {}

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_manifest(manifest: dict):

    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _file_hash(text: str) -> str:

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# Parse a knowledge-base document into (metadata, sections)
#
# Expected format:
#
#   TITLE: ...
#   CATEGORY: ...
#   DOC_TYPE: ...
#   LAST_UPDATED: ...
#   ===
#   ## Section Heading
#   body text...
#
#   ## Another Section
#   body text...
#
# Files that don't follow this format still load, they just fall
# back to filename-derived metadata and treat the whole file as one
# section, so ingestion never hard-fails on an unexpected document.
# ---------------------------------------------------------

def parse_document(filename: str, raw_text: str):

    metadata = {
        "title": filename,
        "category": "General",
        "doc_type": "patient_education",
        "last_updated": None
    }

    body = raw_text

    if "===" in raw_text:

        header_block, _, body = raw_text.partition("===")

        for line in header_block.splitlines():

            line = line.strip()

            if not line or ":" not in line:
                continue

            key, _, value = line.partition(":")
            key = key.strip().upper()
            value = value.strip()

            if key == "TITLE":
                metadata["title"] = value
            elif key == "CATEGORY":
                metadata["category"] = value
            elif key == "DOC_TYPE":
                metadata["doc_type"] = value
            elif key == "LAST_UPDATED":
                metadata["last_updated"] = value

    # Split remaining body into sections on "## Heading" lines.
    sections = []
    current_heading = "General"
    current_lines = []

    for line in body.splitlines():

        heading_match = re.match(r"^\s*##\s+(.*)", line)

        if heading_match:

            if current_lines:
                sections.append(
                    (current_heading, "\n".join(current_lines).strip())
                )

            current_heading = heading_match.group(1).strip()
            current_lines = []

        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            (current_heading, "\n".join(current_lines).strip())
        )

    sections = [(h, b) for h, b in sections if b.strip()]

    if not sections:
        sections = [("General", body.strip())]

    return metadata, sections


# ---------------------------------------------------------
# Split a section's text into chunks of roughly CHUNK_SIZE
# characters, breaking on paragraph/sentence boundaries where
# possible and overlapping chunks so context isn't lost at the
# boundary.
# ---------------------------------------------------------

def split_into_chunks(text: str):

    text = text.strip()

    if len(text) <= CHUNK_SIZE:
        return [text]

    # Prefer splitting on paragraph breaks first.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current = ""

    for paragraph in paragraphs:

        candidate = (current + "\n\n" + paragraph).strip() if current else paragraph

        if len(candidate) <= CHUNK_SIZE:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(paragraph) <= CHUNK_SIZE:
            current = paragraph
        else:
            # Paragraph itself is too long -- fall back to a sliding
            # character window with overlap.
            start = 0
            while start < len(paragraph):
                end = start + CHUNK_SIZE
                chunks.append(paragraph[start:end])
                start = end - CHUNK_OVERLAP
            current = ""

    if current:
        chunks.append(current)

    return chunks


# ---------------------------------------------------------
# Load (or re-load) the knowledge base into ChromaDB.
#
# force=True re-embeds every file regardless of whether its
# content hash changed. Otherwise, unchanged files are skipped so
# re-indexing is cheap and doesn't create duplicate chunks.
# ---------------------------------------------------------

def load_knowledge_base(force: bool = False):

    if not os.path.exists(KNOWLEDGE_BASE_DIR):

        raise FileNotFoundError(
            f"Knowledge base not found: {KNOWLEDGE_BASE_DIR}"
        )

    manifest = _load_manifest()
    new_manifest = {}

    files_processed = 0
    files_skipped = 0
    chunks_loaded = 0

    filenames = sorted(
        f for f in os.listdir(KNOWLEDGE_BASE_DIR)
        if f.lower().endswith(".txt")
    )

    for filename in filenames:

        file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)

        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        if not raw_text.strip():
            continue

        content_hash = _file_hash(raw_text)
        new_manifest[filename] = content_hash

        if not force and manifest.get(filename) == content_hash:
            files_skipped += 1
            continue

        metadata, sections = parse_document(filename, raw_text)

        # Re-indexing: drop any previously stored chunks for this file
        # first, so a shrunk or restructured document doesn't leave
        # orphaned stale chunks behind.
        delete_by_source(filename)

        document_ids = []
        texts = []
        metadatas = []
        chunk_index = 0

        for section_heading, section_body in sections:

            for chunk_text in split_into_chunks(section_body):

                chunk_id = f"{filename}::chunk::{chunk_index}"

                document_ids.append(chunk_id)
                texts.append(chunk_text)
                metadatas.append({
                    "source": filename,
                    "title": metadata["title"],
                    "category": metadata["category"],
                    "doc_type": metadata["doc_type"],
                    "last_updated": metadata["last_updated"] or "",
                    "section": section_heading,
                    "chunk_index": chunk_index
                })

                chunk_index += 1

        add_documents_batch(document_ids, texts, metadatas)

        print(f"Indexed {filename}: {chunk_index} chunks")

        chunks_loaded += chunk_index
        files_processed += 1

    _save_manifest(new_manifest)

    print(
        f"\nKnowledge base ingestion complete. "
        f"Files processed: {files_processed}, "
        f"files unchanged/skipped: {files_skipped}, "
        f"chunks written: {chunks_loaded}"
    )

    return {
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "chunks_loaded": chunks_loaded,
        "total_chunks": get_document_count()
    }


# ---------------------------------------------------------
# Run loader directly: python -m app.services.rag.knowledge_loader
# ---------------------------------------------------------

if __name__ == "__main__":

    clear_collection()

    result = load_knowledge_base(force=True)

    print(f"\nTotal documents in ChromaDB: {result['total_chunks']}")
