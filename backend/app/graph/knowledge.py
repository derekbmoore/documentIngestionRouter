"""
Graph Knowledge (Gk) — Entity Extraction & Relationship Builder
==================================================================
Extracts named entities from ingested chunks and builds a property
graph in PostgreSQL (nodes + edges with JSONB properties).

NIST AI RMF: MAP 1.5 — Entity relationships preserve document context.
"""

import uuid
import structlog
from typing import List, Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.router.models import Chunk, GraphNode, GraphEdge, GraphQueryResult

logger = structlog.get_logger()


class KnowledgeGraphBuilder:
    """
    Builds and queries a property graph from ingested documents.

    Pipeline:
    1. Extract entities (NER via spaCy)
    2. Create/update graph nodes
    3. Create edges between co-occurring entities
    4. Link nodes to source documents
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.warning("spaCy not available", error=str(e))
        return self._nlp

    async def build_from_chunks(
        self,
        chunks: List[Chunk],
        document_id: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Extract entities from chunks and build graph."""
        nlp = self._get_nlp()
        if nlp is None:
            return {"nodes_created": 0, "edges_created": 0}

        all_entities: List[Dict[str, str]] = []
        nodes_created = 0
        edges_created = 0

        for chunk in chunks:
            doc = nlp(chunk.text[:5000])  # limit for performance
            entities = [
                {"text": ent.text, "label": ent.label_}
                for ent in doc.ents
                if len(ent.text) > 2
            ]
            all_entities.extend(entities)

        # Deduplicate entities by normalized text
        unique_entities: Dict[str, Dict[str, str]] = {}
        for ent in all_entities:
            key = ent["text"].lower().strip()
            if key not in unique_entities:
                unique_entities[key] = ent

        # Create/update nodes
        node_ids: Dict[str, str] = {}
        for key, ent in unique_entities.items():
            node_id = await self._upsert_node(
                label=ent["text"],
                entity_type=ent["label"],
                document_id=document_id,
                tenant_id=tenant_id,
            )
            node_ids[key] = node_id
            nodes_created += 1

        # Create edges between co-occurring entities
        keys = list(node_ids.keys())
        for i in range(len(keys)):
            for j in range(i + 1, min(i + 5, len(keys))):  # window of 5
                edge_id = await self._upsert_edge(
                    source_id=node_ids[keys[i]],
                    target_id=node_ids[keys[j]],
                    relationship="co_occurs",
                    tenant_id=tenant_id,
                )
                if edge_id:
                    edges_created += 1

        logger.info(
            "Knowledge graph updated",
            document_id=document_id,
            nodes=nodes_created,
            edges=edges_created,
        )

        return {"nodes_created": nodes_created, "edges_created": edges_created}

    async def _upsert_node(
        self,
        label: str,
        entity_type: str,
        document_id: str,
        tenant_id: Optional[str],
    ) -> str:
        """Create or update a graph node."""
        node_id = uuid.uuid4().hex[:16]

        sql = text("""
            INSERT INTO graph_nodes (id, label, entity_type, document_ids, tenant_id)
            VALUES (:id, :label, :entity_type, ARRAY[:doc_id], :tenant_id)
            ON CONFLICT (id) DO UPDATE
            SET document_ids = array_append(
                COALESCE(graph_nodes.document_ids, ARRAY[]::text[]),
                :doc_id
            )
            RETURNING id
        """)

        # Check if node with this label exists
        check = text("""
            SELECT id FROM graph_nodes
            WHERE lower(label) = lower(:label) AND entity_type = :entity_type
            LIMIT 1
        """)
        result = await self.db.execute(check, {"label": label, "entity_type": entity_type})
        existing = result.fetchone()

        if existing:
            # Update existing node
            update = text("""
                UPDATE graph_nodes
                SET document_ids = array_append(
                    COALESCE(document_ids, ARRAY[]::text[]),
                    :doc_id
                )
                WHERE id = :id
            """)
            await self.db.execute(update, {"id": existing.id, "doc_id": document_id})
            return existing.id
        else:
            await self.db.execute(sql, {
                "id": node_id,
                "label": label,
                "entity_type": entity_type,
                "doc_id": document_id,
                "tenant_id": tenant_id,
            })
            return node_id

    async def _upsert_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        tenant_id: Optional[str],
    ) -> Optional[str]:
        """Create or update a graph edge."""
        check = text("""
            SELECT id, weight FROM graph_edges
            WHERE source_id = :src AND target_id = :tgt AND relationship = :rel
            LIMIT 1
        """)
        result = await self.db.execute(check, {
            "src": source_id, "tgt": target_id, "rel": relationship
        })
        existing = result.fetchone()

        if existing:
            update = text("""
                UPDATE graph_edges SET weight = weight + 1 WHERE id = :id
            """)
            await self.db.execute(update, {"id": existing.id})
            return None  # not a new edge
        else:
            edge_id = uuid.uuid4().hex[:16]
            insert = text("""
                INSERT INTO graph_edges (id, source_id, target_id, relationship, weight, tenant_id)
                VALUES (:id, :src, :tgt, :rel, 1.0, :tenant_id)
            """)
            await self.db.execute(insert, {
                "id": edge_id,
                "src": source_id,
                "tgt": target_id,
                "rel": relationship,
                "tenant_id": tenant_id,
            })
            return edge_id

    async def query(
        self,
        entity: str,
        depth: int = 2,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> GraphQueryResult:
        """Traverse the knowledge graph from an entity."""
        tenant_filter = "AND gn.tenant_id = :tenant_id" if tenant_id else ""

        # Find starting nodes
        sql = text(f"""
            SELECT id, label, entity_type, properties
            FROM graph_nodes gn
            WHERE similarity(gn.label, :entity) > 0.3
            {tenant_filter}
            ORDER BY similarity(gn.label, :entity) DESC
            LIMIT 5
        """)
        params = {"entity": entity, "limit": limit}
        if tenant_id:
            params["tenant_id"] = tenant_id

        result = await self.db.execute(sql, params)
        start_nodes = result.fetchall()

        nodes = [
            GraphNode(id=n.id, label=n.label, entity_type=n.entity_type, properties=n.properties or {})
            for n in start_nodes
        ]

        # Get edges from start nodes
        node_ids = [n.id for n in nodes]
        if not node_ids:
            return GraphQueryResult(nodes=[], edges=[], paths=[])

        edges_sql = text("""
            SELECT ge.id, ge.source_id, ge.target_id, ge.relationship, ge.weight, ge.properties
            FROM graph_edges ge
            WHERE ge.source_id = ANY(:ids) OR ge.target_id = ANY(:ids)
            LIMIT :limit
        """)
        result = await self.db.execute(edges_sql, {"ids": node_ids, "limit": limit})
        edge_rows = result.fetchall()

        edges = [
            GraphEdge(
                id=e.id, source_id=e.source_id, target_id=e.target_id,
                relationship=e.relationship, weight=e.weight,
                properties=e.properties or {},
            )
            for e in edge_rows
        ]

        # Get connected nodes
        connected_ids = set()
        for e in edge_rows:
            connected_ids.add(e.source_id)
            connected_ids.add(e.target_id)
        connected_ids -= set(node_ids)

        if connected_ids:
            conn_sql = text("""
                SELECT id, label, entity_type, properties FROM graph_nodes
                WHERE id = ANY(:ids)
            """)
            result = await self.db.execute(conn_sql, {"ids": list(connected_ids)})
            for n in result.fetchall():
                nodes.append(GraphNode(
                    id=n.id, label=n.label, entity_type=n.entity_type,
                    properties=n.properties or {},
                ))

        return GraphQueryResult(nodes=nodes, edges=edges)
