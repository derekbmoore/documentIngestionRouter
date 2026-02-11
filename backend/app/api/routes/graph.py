"""
Graph Knowledge API — Query the knowledge graph.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.graph.knowledge import KnowledgeGraphBuilder
from app.router.models import GraphQueryResult

router = APIRouter()


@router.get("/graph/query", response_model=GraphQueryResult)
async def query_graph(
    entity: str = Query(..., description="Entity to search for"),
    depth: int = Query(2, ge=1, le=5),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Traverse the knowledge graph starting from an entity."""
    builder = KnowledgeGraphBuilder(db)
    return await builder.query(
        entity=entity, depth=depth, tenant_id=tenant_id, limit=limit,
    )


@router.get("/graph/stats")
async def graph_stats(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge graph statistics."""
    from sqlalchemy import text

    tenant_filter = "WHERE tenant_id = :tid" if tenant_id else ""
    params = {"tid": tenant_id} if tenant_id else {}

    nodes_q = await db.execute(
        text(f"SELECT COUNT(*) FROM graph_nodes {tenant_filter}"), params
    )
    edges_q = await db.execute(
        text(f"SELECT COUNT(*) FROM graph_edges {tenant_filter}"), params
    )
    types_q = await db.execute(text(
        f"SELECT entity_type, COUNT(*) as cnt FROM graph_nodes {tenant_filter} GROUP BY entity_type ORDER BY cnt DESC"
    ), params)

    return {
        "total_nodes": nodes_q.scalar(),
        "total_edges": edges_q.scalar(),
        "entity_types": [
            {"type": r.entity_type, "count": r.cnt}
            for r in types_q.fetchall()
        ],
    }
