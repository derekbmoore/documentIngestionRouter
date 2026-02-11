"""
Document Ingestion Router — Classification Engine
===================================================
Routes documents to appropriate extraction engines based on truth value.

Classification System:
- Class A (Immutable Truth): High-fidelity extraction via Docling
- Class B (Ephemeral Stream): Semantic chunking via Unstructured
- Class C (Operational Pulse): Native handling via Pandas

NIST AI RMF: MAP 1.5 (Boundaries), MANAGE 2.3 (Data Governance)
Part of the Context Ecology (ctxEco) platform.
"""

import logging
import uuid
import os
from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone

import structlog

from app.router.models import (
    DataClass,
    SensitivityLevel,
    DataCategory,
    Chunk,
    ChunkMetadata,
    ClassificationResult,
    IngestResult,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# File-type → Class mappings
# ---------------------------------------------------------------------------
CLASS_A_EXTENSIONS = {".pdf", ".scidoc"}
CLASS_B_EXTENSIONS = {".pptx", ".docx", ".doc", ".eml", ".msg", ".html", ".md", ".txt"}
CLASS_C_EXTENSIONS = {".csv", ".parquet", ".json", ".log", ".jsonl", ".xlsx"}

# Keywords indicating technical / immutable content
TRUTH_KEYWORDS = {
    "manual", "spec", "specification", "standard", "iso", "safety",
    "protocol", "procedure", "guideline", "regulation", "compliance",
    "datasheet", "technical", "engineering", "reference", "nist",
    "fedramp", "stig", "cve", "policy",
}

# Sensitivity keywords
HIGH_SENSITIVITY_KEYWORDS = {"secret", "credential", "password", "ssn", "pii", "phi", "cui"}
MODERATE_SENSITIVITY_KEYWORDS = {"proprietary", "internal", "confidential", "draft"}

# Decay rates per class
DECAY_RATES = {
    DataClass.CLASS_A_TRUTH: 0.01,    # Nearly permanent
    DataClass.CLASS_B_CHATTER: 0.50,  # Moderate decay
    DataClass.CLASS_C_OPS: 0.90,      # Rapid decay
}


class DocumentIngestionRouter:
    """
    Routes documents to appropriate extraction engines based on Truth Value.

    The router classifies documents and delegates to:
    - DoclingEngine:       High-fidelity extraction (tables, layouts)
    - UnstructuredEngine:  Semantic chunking for narrative content
    - PandasEngine:        Native structured data handling

    NIST AI RMF: MANAGE 2.3 — Classification determines governance rules.
    """

    def __init__(
        self,
        fallback_to_unstructured: bool = True,
        docling_enabled: bool = True,
    ):
        self.fallback_to_unstructured = fallback_to_unstructured
        self.docling_enabled = docling_enabled or (
            os.getenv("DOCLING_ENABLED", "true").lower() == "true"
        )
        self._engines = {}
        self._init_engines()

    def _init_engines(self):
        """Lazy-load extraction engines."""
        from app.engines.docling_engine import DoclingEngine
        from app.engines.unstructured_engine import UnstructuredEngine
        from app.engines.pandas_engine import PandasEngine

        self._engines = {
            DataClass.CLASS_A_TRUTH: DoclingEngine(),
            DataClass.CLASS_B_CHATTER: UnstructuredEngine(),
            DataClass.CLASS_C_OPS: PandasEngine(),
        }

    # -----------------------------------------------------------------
    # Classification
    # -----------------------------------------------------------------
    def classify(self, file_path: str) -> ClassificationResult:
        """
        Classify a file by truth value and sensitivity.

        NIST AI RMF: MANAGE 2.3 — Classification is the first governance step.
        NIST SP 800-60  — Sensitivity classification (High / Moderate / Low).
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        filename_lower = path.name.lower()

        # --- Data class ---
        data_class, reason = self._classify_by_extension(ext, filename_lower)

        # --- Sensitivity ---
        sensitivity = self._classify_sensitivity(filename_lower)
        categories = self._detect_categories(filename_lower)
        frameworks = self._detect_frameworks(filename_lower)
        decay_rate = DECAY_RATES.get(data_class, 0.5)

        return ClassificationResult(
            data_class=data_class,
            reason=reason,
            sensitivity_level=sensitivity,
            data_categories=categories,
            decay_rate=decay_rate,
            requires_encryption=(sensitivity == SensitivityLevel.HIGH),
            compliance_frameworks=frameworks,
            confidence=0.85 if data_class == DataClass.CLASS_A_TRUTH else 0.70,
        )

    def _classify_by_extension(
        self, ext: str, filename_lower: str
    ) -> Tuple[DataClass, str]:
        if ext in CLASS_A_EXTENSIONS:
            return DataClass.CLASS_A_TRUTH, f"Extension {ext} → technical document"
        if ext in CLASS_C_EXTENSIONS:
            return DataClass.CLASS_C_OPS, f"Extension {ext} → operational data"
        if ext in CLASS_B_EXTENSIONS:
            if self._is_technical_document(filename_lower):
                return DataClass.CLASS_A_TRUTH, "Filename keywords → technical document"
            return DataClass.CLASS_B_CHATTER, f"Extension {ext} → ephemeral content"
        return DataClass.CLASS_B_CHATTER, "Unknown type, defaulting to ephemeral"

    def _is_technical_document(self, filename: str) -> bool:
        return any(kw in filename for kw in TRUTH_KEYWORDS)

    def _classify_sensitivity(self, filename: str) -> SensitivityLevel:
        if any(kw in filename for kw in HIGH_SENSITIVITY_KEYWORDS):
            return SensitivityLevel.HIGH
        if any(kw in filename for kw in MODERATE_SENSITIVITY_KEYWORDS):
            return SensitivityLevel.MODERATE
        return SensitivityLevel.LOW

    def _detect_categories(self, filename: str) -> List[DataCategory]:
        cats = []
        if "pii" in filename or "ssn" in filename:
            cats.append(DataCategory.PII)
        if "phi" in filename or "hipaa" in filename:
            cats.append(DataCategory.PHI)
        if "cui" in filename:
            cats.append(DataCategory.CUI)
        if "safety" in filename:
            cats.append(DataCategory.SAFETY)
        if "proprietary" in filename:
            cats.append(DataCategory.PROPRIETARY)
        return cats or [DataCategory.INTERNAL]

    def _detect_frameworks(self, filename: str) -> List[str]:
        frameworks = []
        if "nist" in filename:
            frameworks.append("NIST AI RMF")
        if "fedramp" in filename:
            frameworks.append("FedRAMP")
        if "iso" in filename:
            frameworks.append("ISO 27001")
        if "hipaa" in filename:
            frameworks.append("HIPAA")
        return frameworks

    # -----------------------------------------------------------------
    # Ingestion
    # -----------------------------------------------------------------
    async def ingest(
        self,
        file_path: str,
        filename: Optional[str] = None,
        force_class: Optional[DataClass] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        acl_groups: Optional[List[str]] = None,
    ) -> Tuple[List[Chunk], ClassificationResult]:
        """
        Ingest a document: classify → extract → enrich metadata.

        NIST AI RMF:
        - MAP 1.5:     Provenance preserved in chunk metadata
        - MANAGE 2.3:  Classification determines processing
        - MEASURE 2.1: Extraction quality auditable
        """
        display_name = filename or Path(file_path).name

        # Classify
        classification = self.classify(file_path)
        if force_class:
            classification.data_class = force_class
            classification.reason = "Forced classification override"

        logger.info(
            "Document classified",
            filename=display_name,
            data_class=classification.data_class.value,
            reason=classification.reason,
            sensitivity=classification.sensitivity_level.value,
        )

        # Generate provenance
        provenance_id = f"{classification.data_class.value[0]}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        # Extract via engine
        chunks = await self._execute_engine(
            file_path, display_name, classification.data_class
        )

        # Enrich metadata
        for chunk in chunks:
            chunk.metadata.provenance_id = provenance_id
            chunk.metadata.data_class = classification.data_class.value
            chunk.metadata.source_file = display_name
            chunk.metadata.ingested_at = now
            chunk.metadata.decay_rate = classification.decay_rate
            chunk.metadata.sensitivity_level = classification.sensitivity_level.value
            chunk.metadata.data_categories = [c.value for c in classification.data_categories]
            chunk.metadata.user_id = user_id
            chunk.metadata.tenant_id = tenant_id
            chunk.metadata.acl_groups = acl_groups or []
            chunk.metadata.compliance_frameworks = classification.compliance_frameworks

        logger.info(
            "Ingestion complete",
            filename=display_name,
            chunks=len(chunks),
            provenance=provenance_id,
        )

        return chunks, classification

    async def ingest_bytes(
        self,
        content: bytes,
        filename: str,
        force_class: Optional[DataClass] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        acl_groups: Optional[List[str]] = None,
    ) -> Tuple[List[Chunk], ClassificationResult]:
        """Ingest from raw bytes (file upload). Writes to temp file."""
        import tempfile

        ext = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            return await self.ingest(
                file_path=tmp_path,
                filename=filename,
                force_class=force_class,
                user_id=user_id,
                tenant_id=tenant_id,
                acl_groups=acl_groups,
            )
        finally:
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass

    async def _execute_engine(
        self, file_path: str, filename: str, data_class: DataClass
    ) -> List[Chunk]:
        """Route to the correct extraction engine."""
        engine = self._engines.get(data_class)

        if data_class == DataClass.CLASS_A_TRUTH and not self.docling_enabled:
            if self.fallback_to_unstructured:
                logger.warning("Docling disabled, falling back to Unstructured")
                engine = self._engines[DataClass.CLASS_B_CHATTER]
            else:
                raise RuntimeError("Docling is disabled and fallback is off")

        if engine is None:
            raise ValueError(f"No engine for class: {data_class}")

        try:
            return await engine.extract(file_path)
        except Exception as e:
            if (
                data_class == DataClass.CLASS_A_TRUTH
                and self.fallback_to_unstructured
            ):
                logger.warning("Engine failed, falling back", error=str(e))
                return await self._engines[DataClass.CLASS_B_CHATTER].extract(
                    file_path
                )
            raise


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_router_instance: Optional[DocumentIngestionRouter] = None


def get_router() -> DocumentIngestionRouter:
    """Get / create the singleton router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = DocumentIngestionRouter()
    return _router_instance
