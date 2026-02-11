"""
Temporal Worker — Runs ingestion workflow activities.
"""

import asyncio
import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from app.config import settings
from app.workflows.ingestion import (
    IngestionWorkflow,
    classify_document_activity,
    extract_chunks_activity,
    generate_embeddings_activity,
    build_graph_activity,
    persist_chunks_activity,
)

logger = structlog.get_logger()

TASK_QUEUE = "doc-ingestion-queue"


async def main():
    logger.info("Starting Temporal worker", host=settings.temporal_host)

    client = await Client.connect(settings.temporal_host)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[IngestionWorkflow],
        activities=[
            classify_document_activity,
            extract_chunks_activity,
            generate_embeddings_activity,
            build_graph_activity,
            persist_chunks_activity,
        ],
    )

    logger.info("Worker running", task_queue=TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
