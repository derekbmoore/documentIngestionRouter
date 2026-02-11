"""
Unstructured Extraction Engine — Class B (Ephemeral Stream)
=============================================================
Semantic chunking via Unstructured.io.

Provides:
- Header-based splitting
- Element type detection (title, narrative, table)
- Metadata extraction

NIST AI RMF: MEASURE 2.1 — Extraction quality is auditable.
"""

import structlog
from typing import List

from app.engines.base import BaseEngine
from app.router.models import Chunk, ChunkMetadata

logger = structlog.get_logger()


class UnstructuredEngine(BaseEngine):
    """Class B engine — semantic chunking via Unstructured.io."""

    async def extract(self, file_path: str) -> List[Chunk]:
        try:
            from unstructured.partition.auto import partition

            elements = partition(filename=file_path)

            chunks = [
                Chunk(
                    text=str(element),
                    metadata=ChunkMetadata(
                        element_type=getattr(element, "category", "text"),
                    ),
                )
                for element in elements
                if str(element).strip()
            ]

            logger.info("Unstructured extraction complete", chunks=len(chunks))
            return chunks

        except ImportError:
            logger.warning(
                "Unstructured not installed — falling back to simple extraction"
            )
            return await self._simple_fallback(file_path)
        except Exception as e:
            logger.error("Unstructured extraction failed", error=str(e))
            return await self._simple_fallback(file_path)
