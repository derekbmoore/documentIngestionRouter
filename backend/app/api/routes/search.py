"""
Search API — TriSearch™ (Keyword + Vector + Graph Knowledge).
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.router.models import SearchMode, SearchResponse
from app.search.trisearch import TriSearchEngine
from app.core.security_context import SecurityContext
from app.api.middleware.auth import get_current_user
from app.core.audit import AuditEventType, audit_log

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    mode: SearchMode = Query(SearchMode.TRISEARCH, description="Search mode"),
    limit: int = Query(20, ge=1, le=100),
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    TriSearch™ — Unified search across keyword, vector, and graph knowledge.

    Modes:
    - keyword:   PostgreSQL tsvector full-text search
    - vector:    pgvector cosine similarity (requires embeddings)
    - graph:     Knowledge graph entity traversal
    - trisearch: Reciprocal Rank Fusion of all three

    Security: tenant_id is MANDATORY from SecurityContext — no cross-tenant leakage.
    """
    # Audit log the search
    audit_log(
        AuditEventType.RESOURCE_SEARCH,
        action="search",
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        details={"query": q, "mode": mode.value, "limit": limit},
    )

    engine = TriSearchEngine(db)
    return await engine.search(
        query=q,
        mode=mode,
        tenant_id=ctx.tenant_id,
        limit=limit,
    )
