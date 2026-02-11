"""
Database Models — SQLAlchemy ORM
==================================
Documents, chunks, embeddings, graph nodes/edges.

Uses pgvector for vector storage, tsvector for full-text,
JSONB for graph properties.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, Boolean,
    ForeignKey, Index, JSON,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Document(Base):
    """An ingested document."""
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True)
    filename = Column(String(512), nullable=False)
    data_class = Column(String(32), nullable=False, index=True)
    sensitivity_level = Column(String(16), default="low")
    data_categories = Column(ARRAY(String), default=[])
    compliance_frameworks = Column(ARRAY(String), default=[])
    decay_rate = Column(Float, default=0.5)
    provenance_id = Column(String(32), nullable=False, unique=True)
    source_connector = Column(String(32), default="local")
    tenant_id = Column(String(64), index=True)
    user_id = Column(String(64))
    acl_groups = Column(ARRAY(String), default=[])
    chunk_count = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    mime_type = Column(String(128))
    ingested_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSONB, default={})

    chunks = relationship("ChunkRecord", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_tenant_class", "tenant_id", "data_class"),
    )


class ChunkRecord(Base):
    """A chunk of extracted text with embedding."""
    __tablename__ = "chunks"

    id = Column(String(64), primary_key=True)
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # text-embedding-ada-002 = 1536 dims
    element_type = Column(String(32))
    page = Column(Integer)
    row_index = Column(Integer)
    data_class = Column(String(32), index=True)
    provenance_id = Column(String(32))
    decay_rate = Column(Float, default=0.5)
    tenant_id = Column(String(64), index=True)

    # Full-text search vector (auto-populated by trigger)
    search_vector = Column(TSVECTOR)

    metadata_json = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_chunks_embedding", "embedding", postgresql_using="ivfflat",
              postgresql_with={"lists": 100},
              postgresql_ops={"embedding": "vector_cosine_ops"}),
        Index("ix_chunks_tenant_class", "tenant_id", "data_class"),
    )


class GraphNodeRecord(Base):
    """A node in the knowledge graph."""
    __tablename__ = "graph_nodes"

    id = Column(String(64), primary_key=True)
    label = Column(String(512), nullable=False)
    entity_type = Column(String(64), nullable=False, index=True)
    properties = Column(JSONB, default={})
    document_ids = Column(ARRAY(String), default=[])
    tenant_id = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_graph_nodes_label", "label"),
    )


class GraphEdgeRecord(Base):
    """An edge in the knowledge graph."""
    __tablename__ = "graph_edges"

    id = Column(String(64), primary_key=True)
    source_id = Column(String(64), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(String(64), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    relationship = Column(String(128), nullable=False)
    weight = Column(Float, default=1.0)
    properties = Column(JSONB, default={})
    tenant_id = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_graph_edges_source", "source_id"),
        Index("ix_graph_edges_target", "target_id"),
        Index("ix_graph_edges_rel", "relationship"),
    )


class ConnectorRecord(Base):
    """Persisted connector configuration."""
    __tablename__ = "connectors"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    kind = Column(String(32), nullable=False)
    status = Column(String(16), default="pending")
    config_json = Column(JSONB, default={})
    default_class = Column(String(32), default="ephemeral_stream")
    sensitivity_level = Column(String(16), default="low")
    last_sync = Column(DateTime)
    docs_ingested = Column(Integer, default=0)
    error_message = Column(Text)
    tenant_id = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """NIST AI RMF / FedRAMP audit trail."""
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(32))
    resource_id = Column(String(64))
    user_id = Column(String(64))
    tenant_id = Column(String(64))
    details = Column(JSONB, default={})
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
