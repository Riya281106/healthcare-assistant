import time
import traceback

from fastapi import APIRouter, HTTPException

from app.services.rag.vector_store import (
    get_document_count,
    get_source_stats
)
from app.services.rag.knowledge_loader import load_knowledge_base


router = APIRouter(prefix="/api/rag", tags=["rag"])


# ==================================================
# KNOWLEDGE BASE STATS
# Powers the "Knowledge / Sources" frontend page.
# ==================================================

@router.get("/stats")
def rag_stats():

    try:

        sources = get_source_stats()

        categories = sorted({s["category"] for s in sources})

        return {
            "total_documents": len(sources),
            "total_chunks": get_document_count(),
            "categories": categories,
            "sources": sources
        }

    except Exception as e:

        traceback.print_exc()

        raise HTTPException(status_code=500, detail=str(e))


# ==================================================
# RE-INDEX KNOWLEDGE BASE
# Re-embeds any knowledge-base file that changed since the
# last run (or every file, if force=true). This is a real
# ingestion run, not a UI-only refresh.
# ==================================================

@router.post("/reindex")
def rag_reindex(force: bool = False):

    try:

        start = time.time()

        result = load_knowledge_base(force=force)

        result["duration_seconds"] = round(time.time() - start, 3)

        return result

    except FileNotFoundError as e:

        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:

        traceback.print_exc()

        raise HTTPException(status_code=500, detail=str(e))
