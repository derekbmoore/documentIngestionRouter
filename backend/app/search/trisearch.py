"""
TriSearch™ — Keyword + Vector + Graph Knowledge Fusion
========================================================
Orchestrates three search modalities and fuses results via
Reciprocal Rank Fusion (RRF).

NIST AI RMF: MEASURE 2.1 — Search quality is auditable.
"""

import uuid
import structlog
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.router.models import SearchResult, SearchResponse, SearchMode

logger = structlog.get_logger()


class TriSearchEngine:
    """
    TriSearch™ orchestrator.

    Combines:
    - Keyword: PostgreSQL tsvector/tsquery full-text search
    - Vector:  pgvector cosine similarity
    - Graph:   Knowledge graph traversal
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.TRISEARCH,
        tenant_id: Optional[str] = None,
        limit: int = 20,
        k: int = 60,  # RRF constant
    ) -> SearchResponse:
        """Execute search across all or individual modalities."""

        keyword_results: List[SearchResult] = []
        vector_results: List[SearchResult] = []
        graph_results: List[SearchResult] = []

        if mode in (SearchMode.KEYWORD, SearchMode.TRISEARCH):
            keyword_results = await self._keyword_search(query, tenant_id, limit)

        if mode in (SearchMode.VECTOR, SearchMode.TRISEARCH):
            vector_results = await self._vector_search(query, tenant_id, limit)

        if mode in (SearchMode.GRAPH, SearchMode.TRISEARCH):
            graph_results = await self._graph_search(query, tenant_id, limit)

        if mode == SearchMode.TRISEARCH:
            fused = self._reciprocal_rank_fusion(
                [keyword_results, vector_results, graph_results], k=k
            )
            results = fused[:limit]
        elif mode == SearchMode.KEYWORD:
            results = keyword_results
        elif mode == SearchMode.VECTOR:
            results = vector_results
        else:
            results = graph_results

        return SearchResponse(
            query=query,
            mode=mode.value,
            results=results,
            total=len(results),
            keyword_count=len(keyword_results),
            vector_count=len(vector_results),
            graph_count=len(graph_results),
        )

    # -----------------------------------------------------------------
    # Keyword search (tsvector)
    # -----------------------------------------------------------------
    async def _keyword_search(
        self, query: str, tenant_id: Optional[str], limit: int
    ) -> List[SearchResult]:
        tenant_filter = "AND c.tenant_id = :tenant_id" if tenant_id else ""
        sql = text(f"""
            SELECT c.id, c.text, c.data_class, c.provenance_id,
                   d.filename AS source_file,
                   ts_rank(c.search_vector, plainto_tsquery('english', :query)) AS score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.search_vector @@ plainto_tsquery('english', :query)
            {tenant_filter}
            ORDER BY score DESC
            LIMIT :limit
        """)
        params = {"query": query, "limit": limit}
        if tenant_id:
            params["tenant_id"] = tenant_id

        result = await self.db.execute(sql, params)
        rows = result.fetchall()

        return [
            SearchResult(
                chunk_id=r.id,
                text=r.text[:500],
                score=float(r.score),
                source_file=r.source_file,
                data_class=r.data_class,
                search_mode="keyword",
            )
            for r in rows
        ]

    # -----------------------------------------------------------------
    # Vector search (pgvector cosine)
    # -----------------------------------------------------------------
    async def _vector_search(
        self, query: str, tenant_id: Optional[str], limit: int
    ) -> List[SearchResult]:
        # Generate embedding for query
        embedding = await self._get_embedding(query)
        if not embedding:
            return []

        tenant_filter = "AND c.tenant_id = :tenant_id" if tenant_id else ""
        sql = text(f"""
            SELECT c.id, c.text, c.data_class, c.provenance_id,
                   d.filename AS source_file,
                   1 - (c.embedding <=> :embedding::vector) AS score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.embedding IS NOT NULL
            {tenant_filter}
            ORDER BY c.embedding <=> :embedding::vector
            LIMIT :limit
        """)
        params = {"embedding": str(embedding), "limit": limit}
        if tenant_id:
            params["tenant_id"] = tenant_id

        result = await self.db.execute(sql, params)
        rows = result.fetchall()

        return [
            SearchResult(
                chunk_id=r.id,
                text=r.text[:500],
                score=float(r.score),
                source_file=r.source_file,
                data_class=r.data_class,
                search_mode="vector",
            )
            for r in rows
        ]

    # -----------------------------------------------------------------
    # Graph Knowledge search
    # -----------------------------------------------------------------
    async def _graph_search(
        self, query: str, tenant_id: Optional[str], limit: int
    ) -> List[SearchResult]:
        """Find chunks connected to entities matching the query."""
        tenant_filter = "AND gn.tenant_id = :tenant_id" if tenant_id else ""
        sql = text(f"""
            WITH matched_nodes AS (
                SELECT gn.id, gn.label, gn.entity_type,
                       similarity(gn.label, :query) AS sim
                FROM graph_nodes gn
                WHERE similarity(gn.label, :query) > 0.3
                {tenant_filter}
                ORDER BY sim DESC
                LIMIT 10
            ),
            connected AS (
                SELECT DISTINCT unnest(gn.document_ids) AS doc_id
                FROM matched_nodes mn
                JOIN graph_nodes gn ON gn.id = mn.id
                UNION
                SELECT DISTINCT unnest(gn2.document_ids) AS doc_id
                FROM matched_nodes mn
                JOIN graph_edges ge ON ge.source_id = mn.id OR ge.target_id = mn.id
                JOIN graph_nodes gn2 ON gn2.id = (
                    CASE WHEN ge.source_id = mn.id THEN ge.target_id ELSE ge.source_id END
                )
            )
            SELECT c.id, c.text, c.data_class, c.provenance_id,
                   d.filename AS source_file,
                   0.7 AS score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.document_id IN (SELECT doc_id FROM connected)
            LIMIT :limit
        """)
        params = {"query": query, "limit": limit}
        if tenant_id:
            params["tenant_id"] = tenant_id

        try:
            result = await self.db.execute(sql, params)
            rows = result.fetchall()
        except Exception as e:
            logger.warning("Graph search failed", error=str(e))
            return []

        return [
            SearchResult(
                chunk_id=r.id,
                text=r.text[:500],
                score=float(r.score),
                source_file=r.source_file,
                data_class=r.data_class,
                search_mode="graph",
            )
            for r in rows
        ]

    # -----------------------------------------------------------------
    # Reciprocal Rank Fusion
    # -----------------------------------------------------------------
    def _reciprocal_rank_fusion(
        self, result_lists: List[List[SearchResult]], k: int = 60
    ) -> List[SearchResult]:
        """Fuse multiple ranked lists using RRF."""
        scores: dict[str, float] = {}
        best_result: dict[str, SearchResult] = {}

        for results in result_lists:
            for rank, r in enumerate(results, start=1):
                rrf_score = 1.0 / (k + rank)
                scores[r.chunk_id] = scores.get(r.chunk_id, 0.0) + rrf_score
                if r.chunk_id not in best_result:
                    best_result[r.chunk_id] = r

        fused = []
        for chunk_id, score in sorted(scores.items(), key=lambda x: -x[1]):
            r = best_result[chunk_id]
            r.score = score
            r.search_mode = "trisearch"
            fused.append(r)

        return fused

    # -----------------------------------------------------------------
    # Embedding helper
    # -----------------------------------------------------------------
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding via Azure OpenAI."""
        from app.config import settings

        if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
            logger.warning("Azure OpenAI not configured — vector search disabled")
            return None

        try:
            from openai import AsyncAzureOpenAI

            client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version="2024-02-01",
            )
            response = await client.embeddings.create(
                input=text,
                model=settings.azure_openai_embedding_deployment,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            return None
