"""
Temporal Workflow — Durable Document Ingestion
================================================
Orchestrates long-running ingestion workflows with retry,
progress tracking, and failure recovery.

NIST AI RMF: GOVERN 1.1 — Workflow orchestration is auditable.
"""

import structlog
from datetime import timedelta

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
@activity.defn
async def classify_document_activity(file_path: str, filename: str) -> dict:
    """Classify a document and return the classification result."""
    from app.router.classifier import get_router

    router = get_router()
    classification = router.classify(file_path)
    return {
        "data_class": classification.data_class.value,
        "reason": classification.reason,
        "sensitivity": classification.sensitivity_level.value,
        "decay_rate": classification.decay_rate,
    }


@activity.defn
async def extract_chunks_activity(
    file_path: str, filename: str, data_class: str
) -> list:
    """Extract chunks from a document."""
    from app.router.classifier import get_router
    from app.router.models import DataClass

    router = get_router()
    dc = DataClass(data_class)
    chunks, _ = await router.ingest(file_path, filename, force_class=dc)
    return [{"text": c.text, "metadata": c.metadata.model_dump()} for c in chunks]


@activity.defn
async def generate_embeddings_activity(chunks: list) -> list:
    """Generate embeddings for a batch of chunks."""
    from app.config import settings

    if not settings.azure_openai_endpoint:
        return chunks

    try:
        from openai import AsyncAzureOpenAI

        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01",
        )

        for chunk in chunks:
            resp = await client.embeddings.create(
                input=chunk["text"][:8191],
                model=settings.azure_openai_embedding_deployment,
            )
            chunk["embedding"] = resp.data[0].embedding

    except Exception as e:
        logger.error("Embedding batch failed", error=str(e))

    return chunks


@activity.defn
async def build_graph_activity(chunks: list, document_id: str, tenant_id: str) -> dict:
    """Build knowledge graph from extracted chunks."""
    from app.db.session import async_session
    from app.graph.knowledge import KnowledgeGraphBuilder
    from app.router.models import Chunk, ChunkMetadata

    chunk_objects = [
        Chunk(text=c["text"], metadata=ChunkMetadata(**c.get("metadata", {})))
        for c in chunks
    ]

    async with async_session() as db:
        builder = KnowledgeGraphBuilder(db)
        result = await builder.build_from_chunks(chunk_objects, document_id, tenant_id)
        await db.commit()

    return result


@activity.defn
async def persist_chunks_activity(
    chunks: list, document_id: str, data_class: str, tenant_id: str
) -> int:
    """Persist chunks to PostgreSQL."""
    from app.db.session import async_session
    from app.db.models import ChunkRecord

    async with async_session() as db:
        for i, chunk in enumerate(chunks):
            record = ChunkRecord(
                id=f"{document_id}-{i:04d}",
                document_id=document_id,
                text=chunk["text"],
                embedding=chunk.get("embedding"),
                element_type=chunk.get("metadata", {}).get("element_type"),
                page=chunk.get("metadata", {}).get("page"),
                data_class=data_class,
                decay_rate=chunk.get("metadata", {}).get("decay_rate", 0.5),
                tenant_id=tenant_id,
            )
            db.add(record)
        await db.commit()

    return len(chunks)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
@workflow.defn
class IngestionWorkflow:
    """
    Durable ingestion workflow.

    Steps:
    1. Classify document
    2. Extract chunks
    3. Generate embeddings
    4. Build knowledge graph
    5. Persist to database
    """

    @workflow.run
    async def run(
        self,
        file_path: str,
        filename: str,
        document_id: str,
        tenant_id: str = "",
    ) -> dict:
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=5),
            maximum_attempts=3,
        )

        # 1. Classify
        classification = await workflow.execute_activity(
            classify_document_activity,
            args=[file_path, filename],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )

        # 2. Extract
        chunks = await workflow.execute_activity(
            extract_chunks_activity,
            args=[file_path, filename, classification["data_class"]],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
        )

        # 3. Embed
        chunks = await workflow.execute_activity(
            generate_embeddings_activity,
            args=[chunks],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=retry_policy,
        )

        # 4. Graph
        graph_result = await workflow.execute_activity(
            build_graph_activity,
            args=[chunks, document_id, tenant_id],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        # 5. Persist
        chunk_count = await workflow.execute_activity(
            persist_chunks_activity,
            args=[chunks, document_id, classification["data_class"], tenant_id],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        return {
            "document_id": document_id,
            "classification": classification,
            "chunks_processed": chunk_count,
            "graph": graph_result,
            "status": "completed",
        }
