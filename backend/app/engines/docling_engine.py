"""
Docling Extraction Engine — Class A (Immutable Truth)
======================================================
High-fidelity PDF/document extraction using IBM Docling.

Provides:
- TableFormer for table reconstruction
- Bounding box coordinates for provenance
- Multi-column layout preservation

NIST AI RMF: MEASURE 2.1 — Extraction quality is auditable.
"""

import structlog
from typing import List

from app.engines.base import BaseEngine
from app.router.models import Chunk, ChunkMetadata

logger = structlog.get_logger()


class DoclingEngine(BaseEngine):
    """Class A engine — high-fidelity extraction via IBM Docling."""

    async def extract(self, file_path: str) -> List[Chunk]:
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(file_path)

            chunks = []
            for element in result.document.elements:
                text = getattr(element, "text", str(element))
                if not text or not text.strip():
                    continue

                chunks.append(
                    Chunk(
                        text=text,
                        metadata=ChunkMetadata(
                            element_type=getattr(element, "type", "unknown"),
                            page=getattr(element, "page_number", None),
                            bbox=getattr(element, "bbox", None),
                        ),
                    )
                )

            logger.info("Docling extraction complete", chunks=len(chunks))
            return chunks

        except ImportError:
            logger.warning(
                "Docling not installed — falling back to simple extraction"
            )
            return await self._simple_fallback(file_path)
        except Exception as e:
            logger.error("Docling extraction failed", error=str(e))
            raise
