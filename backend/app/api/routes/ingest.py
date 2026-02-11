"""
Ingestion API — Upload, classify, extract, and index resources.
"""

import uuid
import structlog
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.db.models import Document, ChunkRecord
from app.router.classifier import get_router
from app.router.models import DataClass, IngestResult
from app.graph.knowledge import KnowledgeGraphBuilder
from app.search.trisearch import TriSearchEngine
from app.core.security_context import SecurityContext
from app.api.middleware.auth import get_current_user
from app.security.access_policy import ResourceAccessPolicy
from app.core.audit import AuditEventType, audit_log

logger = structlog.get_logger()
router = APIRouter()


@router.post("/ingest", response_model=IngestResult)
async def ingest_document(
    file: UploadFile = File(...),
    force_class: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    team_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    access_level: str = Form("team"),
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and ingest a resource.

    1. Classify by truth value (Class A/B/C)
    2. Extract via appropriate engine (Docling / Unstructured / Pandas)
    3. Generate embeddings
    4. Build knowledge graph entities
    5. Store chunks in PostgreSQL with pgvector

    Security: tenant_id and user_id are injected from the SecurityContext.
    """
    # Read file
    content = await file.read()
    filename = file.filename or "unknown"

    # Validate access_level
    if access_level not in ("private", "team", "project", "tenant"):
        raise HTTPException(400, f"Invalid access_level: {access_level}")

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Parse force_class
    fc = None
    if force_class:
        try:
            fc = DataClass(force_class)
        except ValueError:
            raise HTTPException(400, f"Invalid class: {force_class}")

    # Run ingestion
    ingestion_router = get_router()
    try:
        chunks, classification = await ingestion_router.ingest_bytes(
            content=content,
            filename=filename,
            force_class=fc,
            user_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
        )
    except Exception as e:
        logger.error("Ingestion failed", filename=filename, error=str(e))
        raise HTTPException(500, f"Ingestion failed: {str(e)}")

    # Generate document ID
    doc_id = uuid.uuid4().hex[:16]
    provenance_id = chunks[0].metadata.provenance_id if chunks else f"doc-{doc_id}"

    # Generate embeddings for vector search
    embedding_func = None
    if settings.azure_openai_endpoint and settings.azure_openai_api_key:
        try:
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version="2024-02-01",
            )

            async def generate_embedding(text: str):
                resp = await client.embeddings.create(
                    input=text[:8191],
                    model=settings.azure_openai_embedding_deployment,
                )
                return resp.data[0].embedding

            embedding_func = generate_embedding
        except Exception as e:
            logger.warning("Embedding client init failed", error=str(e))

    # Build ACL groups from user context
    acl_groups = list(ctx.groups) if ctx.groups else []

    # Persist document record
    doc = Document(
        id=doc_id,
        filename=filename,
        data_class=classification.data_class.value,
        sensitivity_level=classification.sensitivity_level.value,
        data_categories=[c.value for c in classification.data_categories],
        compliance_frameworks=classification.compliance_frameworks,
        decay_rate=classification.decay_rate,
        provenance_id=provenance_id,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        acl_groups=acl_groups,
        project_id=project_id or ctx.project_id,
        team_id=team_id or ctx.team_id,
        tags=tag_list,
        access_level=access_level,
        chunk_count=len(chunks),
        file_size_bytes=len(content),
        mime_type=file.content_type,
    )
    db.add(doc)

    # Persist chunks (inherit security metadata from document)
    for i, chunk in enumerate(chunks):
        embedding = None
        if embedding_func:
            try:
                embedding = await embedding_func(chunk.text)
            except Exception:
                pass

        chunk_record = ChunkRecord(
            id=f"{doc_id}-{i:04d}",
            document_id=doc_id,
            text=chunk.text,
            embedding=embedding,
            element_type=chunk.metadata.element_type,
            page=chunk.metadata.page,
            row_index=chunk.metadata.row_index,
            data_class=classification.data_class.value,
            provenance_id=provenance_id,
            decay_rate=classification.decay_rate,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            project_id=project_id or ctx.project_id,
            access_level=access_level,
            acl_groups=acl_groups,
            metadata_json={
                "source_file": filename,
                "sensitivity": classification.sensitivity_level.value,
            },
        )
        db.add(chunk_record)

    await db.commit()

    # Audit log
    audit_log(
        AuditEventType.RESOURCE_INGEST,
        action="ingest",
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        resource=doc_id,
        resource_type="document",
        details={
            "filename": filename,
            "chunks": len(chunks),
            "access_level": access_level,
        },
    )

    # Build knowledge graph (async, non-blocking)
    try:
        graph_builder = KnowledgeGraphBuilder(db)
        await graph_builder.build_from_chunks(chunks, doc_id, ctx.tenant_id)
        await db.commit()
    except Exception as e:
        logger.warning("Graph build failed", error=str(e))

    return IngestResult(
        success=True,
        filename=filename,
        document_id=doc_id,
        chunks_processed=len(chunks),
        message=f"Ingested {len(chunks)} chunks as {classification.data_class.value}",
        classification=classification,
    )


@router.get("/documents")
async def list_documents(
    data_class: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ctx: SecurityContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List ingested documents — scoped to user's tenant and access level."""
    query = select(Document).order_by(Document.ingested_at.desc())

    # MANDATORY: Apply ResourceAccessPolicy filter
    query = ResourceAccessPolicy.build_query_filter(ctx, query, Document)

    if data_class:
        query = query.where(Document.data_class == data_class)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    docs = result.scalars().all()

    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "data_class": d.data_class,
                "sensitivity_level": d.sensitivity_level,
                "access_level": d.access_level,
                "project_id": d.project_id,
                "team_id": d.team_id,
                "chunk_count": d.chunk_count,
                "file_size_bytes": d.file_size_bytes,
                "ingested_at": d.ingested_at.isoformat() if d.ingested_at else None,
                "provenance_id": d.provenance_id,
            }
            for d in docs
        ],
        "total": len(docs),
        "limit": limit,
        "offset": offset,
    }
