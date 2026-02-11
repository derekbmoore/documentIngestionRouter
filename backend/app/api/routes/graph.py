"""
Graph Knowledge API — Query the knowledge graph.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.graph.knowledge import KnowledgeGraphBuilder
from app.router.models import GraphQueryResult
from app.core.security_context import SecurityContext
from app.api.middleware.auth import get_current_user
from app.core.audit import AuditEventType, audit_log

router = APIRouter()


@router.get("/graph/query", response_model=GraphQueryResult)
async def query_graph(
    entity: str = Query(..., description="Entity to search for"),
    depth: int = Query(2, ge=1, le=5),
    limit: int = Query(50, ge=1, le=200),
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Traverse the knowledge graph — scoped to user's tenant."""
    audit_log(
        AuditEventType.GRAPH_QUERY,
        action="graph_query",
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        details={"entity": entity, "depth": depth},
    )

    builder = KnowledgeGraphBuilder(db)
    return await builder.query(
        entity=entity, depth=depth, tenant_id=ctx.tenant_id, limit=limit,
    )


@router.get("/graph/stats")
async def graph_stats(
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge graph statistics — scoped to user's tenant."""
    tenant_filter = "WHERE tenant_id = :tid"
    params = {"tid": ctx.tenant_id}

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
