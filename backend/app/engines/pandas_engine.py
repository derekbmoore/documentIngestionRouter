"""
Pandas Extraction Engine — Class C (Operational Pulse)
========================================================
Native structured data handling via Pandas.

Preserves column structure, numeric precision, and converts
rows directly to vector-ready chunks.

NIST AI RMF: MEASURE 2.1 — Extraction quality is auditable.
"""

import structlog
from pathlib import Path
from typing import List

from app.engines.base import BaseEngine
from app.router.models import Chunk, ChunkMetadata

logger = structlog.get_logger()


class PandasEngine(BaseEngine):
    """Class C engine — structured data via Pandas."""

    async def extract(self, file_path: str) -> List[Chunk]:
        try:
            import pandas as pd
        except ImportError:
            logger.warning("Pandas not installed")
            return []

        ext = Path(file_path).suffix.lower()

        try:
            if ext == ".csv":
                df = pd.read_csv(file_path)
            elif ext == ".parquet":
                df = pd.read_parquet(file_path)
            elif ext in (".json", ".jsonl"):
                df = pd.read_json(file_path, lines=(ext == ".jsonl"))
            elif ext == ".xlsx":
                df = pd.read_excel(file_path)
            elif ext == ".log":
                df = pd.read_csv(file_path, sep=r"\s+", engine="python", on_bad_lines="skip")
            else:
                logger.warning("Unsupported extension for Pandas", ext=ext)
                return []

            columns = list(df.columns)

            chunks = [
                Chunk(
                    text=row.to_json(),
                    metadata=ChunkMetadata(
                        element_type="structured_row",
                        row_index=int(idx),
                        columns=columns,
                    ),
                )
                for idx, row in df.iterrows()
            ]

            logger.info(
                "Pandas extraction complete",
                chunks=len(chunks),
                columns=columns,
            )
            return chunks

        except Exception as e:
            logger.error("Pandas extraction failed", error=str(e))
            return []
