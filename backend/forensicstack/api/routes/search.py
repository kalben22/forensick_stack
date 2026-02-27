from fastapi import APIRouter, Depends, HTTPException

from forensicstack.core.auth import get_current_user
from forensicstack.core.models.user_model import User
from forensicstack.core.chroma_service import get_chroma_service
from forensicstack.api.schemas import SemanticSearchRequest, SemanticSearchResponse

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    _: User = Depends(get_current_user),
):
    """
    Semantic similarity search across all indexed forensic findings.

    Uses sentence-transformer embeddings (all-MiniLM-L6-v2) stored in ChromaDB
    to find findings that are semantically similar to the query — even if they
    don't contain the exact keywords.

    **Examples:**
    - `"process injecting into lsass.exe"`
    - `"suspicious PowerShell execution with encoded command"`
    - `"GPS coordinates found in image metadata"`
    - `"android app accessing contacts without permission"`

    Optionally filter by `case_id` or `tool` to narrow the search.
    """
    chroma = get_chroma_service()
    hits = chroma.search(
        query=request.query,
        n_results=request.top_k,
        case_id=request.case_id,
        tool=request.tool,
    )
    return {
        "query": request.query,
        "total": len(hits),
        "results": hits,
    }


@router.get("/stats")
async def search_stats(_: User = Depends(get_current_user)):
    """Return ChromaDB collection statistics (total indexed findings)."""
    chroma = get_chroma_service()
    return chroma.get_stats()
