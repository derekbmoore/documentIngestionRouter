"""
Search API — TriSearch™ (Keyword + Vector + Graph Knowledge).
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.router.models import SearchMode, SearchResponse
from app.search.trisearch import TriSearchEngine

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    mode: SearchMode = Query(SearchMode.TRISEARCH, description="Search mode"),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    TriSearch™ — Unified search across keyword, vector, and graph knowledge.

    Modes:
    - keyword:   PostgreSQL tsvector full-text search
    - vector:    pgvector cosine similarity (requires embeddings)
    - graph:     Knowledge graph entity traversal
    - trisearch: Reciprocal Rank Fusion of all three
    """
    engine = TriSearchEngine(db)
    return await engine.search(
        query=q,
        mode=mode,
        tenant_id=tenant_id,
        limit=limit,
    )
