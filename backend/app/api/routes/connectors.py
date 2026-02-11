"""
Connectors API — Manage 16 enterprise data source connectors.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.connectors.registry import CONNECTOR_REGISTRY, get_connector
from app.router.models import ConnectorConfig, ConnectorKind

router = APIRouter()


@router.get("/connectors/available")
async def list_available_connectors():
    """List all 16 available connector types and their metadata."""
    connectors = []
    for kind, cls in CONNECTOR_REGISTRY.items():
        instance = cls()
        meta = instance.get_metadata()
        connectors.append(meta)
    return {"connectors": connectors, "total": len(connectors)}


@router.post("/connectors")
async def create_connector(
    config: ConnectorConfig,
    db: AsyncSession = Depends(get_db),
):
    """Register a new data source connector."""
    import uuid
    from app.db.models import ConnectorRecord

    connector_id = config.id or uuid.uuid4().hex[:16]

    record = ConnectorRecord(
        id=connector_id,
        name=config.name,
        kind=config.kind.value,
        status=config.status.value,
        config_json=config.config,
        default_class=config.default_class.value,
        sensitivity_level=config.sensitivity_level.value,
        tenant_id=None,
    )
    db.add(record)
    await db.commit()

    return {"id": connector_id, "message": f"Connector '{config.name}' created"}


@router.get("/connectors")
async def list_connectors(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List configured connectors."""
    from sqlalchemy import select
    from app.db.models import ConnectorRecord

    query = select(ConnectorRecord)
    if tenant_id:
        query = query.where(ConnectorRecord.tenant_id == tenant_id)

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
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity for a configured connector."""
    from sqlalchemy import select
    from app.db.models import ConnectorRecord

    result = await db.execute(
        select(ConnectorRecord).where(ConnectorRecord.id == connector_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Connector not found")

    try:
        connector = get_connector(record.kind, record.config_json)
        ok = await connector.connect()
        return {"status": "success" if ok else "failed", "connector_id": connector_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
