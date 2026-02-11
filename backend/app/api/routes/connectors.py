"""
Connectors API — Manage enterprise data source connectors.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import ConnectorRecord
from app.connectors.registry import CONNECTOR_REGISTRY, get_connector
from app.router.models import ConnectorConfig, ConnectorKind
from app.core.security_context import SecurityContext
from app.api.middleware.auth import get_current_user
from app.security.access_policy import ResourceAccessPolicy
from app.core.audit import AuditEventType, audit_log

router = APIRouter()


@router.get("/connectors/available")
async def list_available_connectors():
    """List all available connector types and their metadata."""
    connectors = []
    for kind, cls in CONNECTOR_REGISTRY.items():
        instance = cls()
        meta = instance.get_metadata()
        connectors.append(meta)
    return {"connectors": connectors, "total": len(connectors)}


@router.post("/connectors")
async def create_connector(
    config: ConnectorConfig,
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new data source connector — scoped to user's tenant."""
    connector_id = config.id or uuid.uuid4().hex[:16]

    record = ConnectorRecord(
        id=connector_id,
        name=config.name,
        kind=config.kind.value,
        status=config.status.value,
        config_json=config.config,
        default_class=config.default_class.value,
        sensitivity_level=config.sensitivity_level.value,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        project_id=ctx.project_id,
        access_level="team",
        acl_groups=list(ctx.groups) if ctx.groups else [],
    )
    db.add(record)
    await db.commit()

    audit_log(
        AuditEventType.CONNECTOR_SYNC,
        action="create_connector",
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        resource=connector_id,
        resource_type="connector",
        details={"name": config.name, "kind": config.kind.value},
    )

    return {"id": connector_id, "message": f"Connector '{config.name}' created"}


@router.get("/connectors")
async def list_connectors(
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List configured connectors — scoped by ResourceAccessPolicy."""
    query = select(ConnectorRecord)

    # MANDATORY: Apply ResourceAccessPolicy filter
    query = ResourceAccessPolicy.build_query_filter(ctx, query, ConnectorRecord)

    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "connectors": [
            {
                "id": r.id,
                "name": r.name,
                "kind": r.kind,
                "status": r.status,
                "default_class": r.default_class,
                "docs_ingested": r.docs_ingested,
                "last_sync": r.last_sync.isoformat() if r.last_sync else None,
                "error_message": r.error_message,
            }
            for r in records
        ],
        "total": len(records),
    }


@router.post("/connectors/{connector_id}/test")
async def test_connector(
    connector_id: str,
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity for a configured connector — tenant-scoped."""
    query = select(ConnectorRecord).where(ConnectorRecord.id == connector_id)

    # Apply access filter so users can only test their own connectors
    query = ResourceAccessPolicy.build_query_filter(ctx, query, ConnectorRecord)

    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Connector not found")

    try:
        connector = get_connector(record.kind, record.config_json)
        ok = await connector.connect()
        return {"status": "success" if ok else "failed", "connector_id": connector_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
