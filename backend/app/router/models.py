"""
Document Ingestion Router — Data Models
========================================
Core Pydantic models for classification, chunks, and ingestion results.

NIST AI RMF: MAP 1.5 — Provenance and boundary definitions.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
class DataClass(str, Enum):
    """Document classification based on truth value."""
    CLASS_A_TRUTH = "immutable_truth"
    CLASS_B_CHATTER = "ephemeral_stream"
    CLASS_C_OPS = "operational_pulse"


class SensitivityLevel(str, Enum):
    """NIST SP 800-60 impact level."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class DataCategory(str, Enum):
    """Data category tags for compliance filtering."""
    PII = "pii"
    PHI = "phi"
    CUI = "cui"
    PCI = "pci"
    PROPRIETARY = "proprietary"
    SAFETY = "safety"
    CREDENTIAL = "credential"
    PUBLIC = "public"
    INTERNAL = "internal"


# ---------------------------------------------------------------------------
# Connector Types
# ---------------------------------------------------------------------------
class ConnectorKind(str, Enum):
    """All 16 supported data source connectors."""
    S3 = "S3"
    AZURE_BLOB = "AzureBlob"
    GCS = "GCS"
    SHAREPOINT = "SharePoint"
    GOOGLE_DRIVE = "GoogleDrive"
    ONEDRIVE = "OneDrive"
    CONFLUENCE = "Confluence"
    SERVICENOW = "ServiceNow"
    JIRA = "Jira"
    GITHUB = "GitHub"
    SLACK = "Slack"
    TEAMS = "Teams"
    EMAIL = "Email"
    DATABASE = "Database"
    WEBHOOK = "Webhook"
    LOCAL = "Local"


class ConnectorCategory(str, Enum):
    CLOUD_STORAGE = "cloud_storage"
    COLLABORATION = "collaboration"
    TICKETING = "ticketing"
    MESSAGING = "messaging"
    DATABASE = "database"
    LOCAL = "local"


# ---------------------------------------------------------------------------
# Chunks & Results
# ---------------------------------------------------------------------------
class ChunkMetadata(BaseModel):
    """Metadata attached to every extracted chunk."""
    provenance_id: str = ""
    data_class: str = ""
    source_file: str = ""
    ingested_at: str = ""
    decay_rate: float = 0.5
    sensitivity_level: Optional[str] = None
    data_categories: List[str] = Field(default_factory=list)
    element_type: Optional[str] = None
    page: Optional[int] = None
    bbox: Optional[Any] = None
    row_index: Optional[int] = None
    columns: Optional[List[str]] = None
    compliance_frameworks: List[str] = Field(default_factory=list)

    # Security
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    access_level: str = "team"
    acl_groups: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class Chunk(BaseModel):
    """A single extracted chunk of content."""
    text: str
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
    embedding: Optional[List[float]] = None


class ClassificationResult(BaseModel):
    """Result of classifying a document."""
    data_class: DataClass
    reason: str
    sensitivity_level: SensitivityLevel = SensitivityLevel.LOW
    data_categories: List[DataCategory] = Field(default_factory=list)
    decay_rate: float = 0.5
    requires_encryption: bool = False
    compliance_frameworks: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class IngestResult(BaseModel):
    """Result of ingesting a document."""
    success: bool
    filename: str
    document_id: str
    chunks_processed: int
    message: str
    classification: ClassificationResult
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    access_level: str = "team"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
class SearchMode(str, Enum):
    KEYWORD = "keyword"
    VECTOR = "vector"
    GRAPH = "graph"
    TRISEARCH = "trisearch"


class SearchResult(BaseModel):
    """A single search result."""
    chunk_id: str
    text: str
    score: float
    source_file: str
    data_class: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    search_mode: str = ""
    project_id: Optional[str] = None
    access_level: str = "team"


class SearchResponse(BaseModel):
    """Complete search response."""
    query: str
    mode: str
    results: List[SearchResult]
    total: int
    keyword_count: int = 0
    vector_count: int = 0
    graph_count: int = 0


# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------
class ConnectorStatus(str, Enum):
    HEALTHY = "healthy"
    INDEXING = "indexing"
    PAUSED = "paused"
    ERROR = "error"
    PENDING = "pending"


class ConnectorConfig(BaseModel):
    """Configuration for a data source connector."""
    id: Optional[str] = None
    name: str
    kind: ConnectorKind
    status: ConnectorStatus = ConnectorStatus.PENDING
    config: Dict[str, Any] = Field(default_factory=dict)
    default_class: DataClass = DataClass.CLASS_B_CHATTER
    sensitivity_level: SensitivityLevel = SensitivityLevel.LOW
    last_sync: Optional[str] = None
    docs_ingested: int = 0
    error_message: Optional[str] = None
    project_id: Optional[str] = None
    access_level: str = "team"
    acl_groups: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Graph Knowledge
# ---------------------------------------------------------------------------
class GraphNode(BaseModel):
    """A node in the knowledge graph."""
    id: str
    label: str
    entity_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
    access_level: str = "team"


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""
    id: str
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
    access_level: str = "team"


class GraphQueryResult(BaseModel):
    """Result of a graph knowledge query."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    paths: List[List[str]] = Field(default_factory=list)
