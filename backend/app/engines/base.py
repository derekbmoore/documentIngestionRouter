"""
Extraction Engine — Base Interface
====================================
All extraction engines implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List

from app.router.models import Chunk


class BaseEngine(ABC):
    """Abstract base for document extraction engines."""

    @abstractmethod
    async def extract(self, file_path: str) -> List[Chunk]:
        """
        Extract chunks from a file.

        Args:
            file_path: Absolute path to the file.

        Returns:
            List of Chunk objects with text and metadata.
        """
        ...

    async def _simple_fallback(self, file_path: str) -> List[Chunk]:
        """Plain-text paragraph splitting as last resort."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            return [
                Chunk(text=p, metadata={"element_type": "text"})
                for p in paragraphs
            ]
        except Exception:
            return []
