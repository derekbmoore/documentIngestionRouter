---
layout: default
title: Research Paper
nav_order: 12
custom_html: true
description: >-
  Truth-Value Classification and Multi-Modal Retrieval in Enterprise Document Ingestion:
  A Defense-in-Depth Architecture for Compliance-Aware Knowledge Systems
---

# Truth-Value Classification and Multi-Modal Retrieval in Enterprise Document Ingestion: A Defense-in-Depth Architecture for Compliance-Aware Knowledge Systems

**derek brent moore**
open source -- mit license

---

## Abstract

Enterprise knowledge management systems face a fundamental tension: the need to ingest heterogeneous document corpora at scale while simultaneously enforcing fine-grained access control, regulatory compliance, and semantic fidelity. This paper presents the Document Ingestion Router, an open-source Model Context Protocol (MCP) server that addresses this tension through three novel contributions. First, we introduce a *truth-value classification* taxonomy that partitions documents into three epistemic classes — Immutable Truth, Ephemeral Stream, and Operational Pulse — each governed by distinct extraction engines, temporal decay functions, and compliance policies. Second, we describe *TriSearch*, a triple-modality retrieval architecture that fuses keyword (BM25), vector (cosine similarity over dense embeddings), and graph knowledge (named-entity co-occurrence traversal) results via Reciprocal Rank Fusion (RRF). Third, we formalize a *Resource Access Policy* (RAP) that enforces four-layer security isolation — tenant, project, team, and user — at the SQL query level, ensuring zero cross-tenant data leakage by construction. The system is designed for deployment in regulated environments and maps directly to controls specified in the NIST AI Risk Management Framework, FedRAMP High baseline, and NIST SP 800-60 sensitivity classification. We describe the architecture, formal models, implementation, and deployment considerations in detail, and discuss implications for the design of compliance-aware AI data pipelines.

**Keywords:** document ingestion, truth-value classification, multi-modal retrieval, reciprocal rank fusion, knowledge graphs, enterprise security, NIST AI RMF, FedRAMP, MCP server, context ecology

---

## 1. Introduction

### 1.1 The Enterprise Document Problem

Modern enterprises generate and consume documents at extraordinary volume and variety. A single organization may simultaneously manage immutable technical specifications (PDFs of engineering standards), ephemeral collaborative content (email threads, slide decks, wiki pages), and high-velocity operational data (telemetry logs, CSV exports, JSON event streams). These document types differ not only in format but in *epistemic character* — the degree to which their content represents stable, authoritative knowledge versus transient, contextual information.

Existing document processing systems treat this heterogeneity as a format problem, dispatching documents to parsers based solely on MIME type or file extension. This approach is insufficient for enterprise knowledge management because it conflates the *structural* properties of a document (how to parse it) with its *epistemic* properties (how to govern, weight, and decay it over time). A PDF containing a NIST Special Publication and a PDF containing meeting minutes require identical parsing but radically different governance, retention, and search-ranking behavior.

### 1.2 The Retrieval Gap

Similarly, enterprise retrieval systems have converged on dense vector search as a default modality, leveraging transformer-based embedding models to capture semantic similarity. While vector search excels at discovering semantically related content across terminological boundaries, it suffers from well-documented limitations: poor handling of exact-match queries (specific error codes, document identifiers, regulatory control numbers), inability to exploit structured entity relationships, and opacity of ranking explanations (Robertson & Zaragoza, 2009; Karpukhin et al., 2020).

Keyword search via inverted indices (BM25, tsvector/tsquery) addresses exact-match requirements but misses conceptual similarity. Knowledge graph traversal captures entity relationships and provenance chains but requires entity extraction infrastructure and operates on a fundamentally different abstraction. No single modality provides comprehensive recall across all enterprise query types.

### 1.3 The Compliance Imperative

Federal agencies and regulated industries increasingly require AI-adjacent systems — including document processing pipelines and retrieval-augmented generation (RAG) backends — to conform to frameworks such as the NIST AI Risk Management Framework (AI RMF), FedRAMP, and NIST SP 800-60. These frameworks mandate provenance tracking (MAP 1.5), data governance classification (MANAGE 2.3), extraction quality auditability (MEASURE 2.1), and explicit policy governance (GOVERN 1.1). Few document ingestion systems are designed with these controls as first-class architectural constraints.

### 1.4 Contributions

This paper presents the Document Ingestion Router, an architecture that unifies three contributions:

1. **Truth-Value Classification (Section 3):** A three-class taxonomy that assigns documents an epistemic classification — Immutable Truth (Class A), Ephemeral Stream (Class B), or Operational Pulse (Class C) — which governs extraction engine selection, temporal decay rate, and compliance policy application.

2. **TriSearch: Triple-Modality Retrieval with RRF (Section 4):** A retrieval architecture that executes keyword, vector, and graph knowledge searches in parallel and fuses their results via Reciprocal Rank Fusion, providing comprehensive recall across exact-match, semantic, and relational query types.

3. **Resource Access Policy with Defense-in-Depth Isolation (Section 5):** A four-layer security model — tenant, project, team, user — enforced at the SQL query level, with mandatory tenant isolation that cannot be bypassed regardless of user role, ensuring compliance with FedRAMP AC-2/AC-6 access control requirements.

The system is implemented as a FastAPI-based MCP server with 16 enterprise data source connectors, Temporal workflow orchestration for durable execution, and Zep-backed episodic memory integration. It is designed for deployment on Azure (commercial and GovCloud) and is open-source under the MIT license as part of the Context Ecology (ctxEco) platform.

---

## 2. Related Work

### 2.1 Document Processing Pipelines

Document processing has evolved from simple format-based parsing (Apache Tika, textract) to sophisticated layout-aware extraction. IBM Docling (Auer et al., 2023) provides high-fidelity PDF processing with TableFormer-based table reconstruction and bounding box coordinate preservation. Unstructured.io offers semantic chunking with header-based splitting and element type detection across diverse formats. These systems operate at the extraction layer but do not address classification, governance, or multi-modal indexing.

LangChain and LlamaIndex provide document loading abstractions for RAG pipelines but treat documents as homogeneous text sources, without epistemic classification or compliance-aware metadata enrichment. Their retrieval implementations typically operate on a single modality (vector search) with optional keyword filtering.

### 2.2 Multi-Modal Retrieval

The fusion of heterogeneous retrieval signals has a rich history in information retrieval. Reciprocal Rank Fusion (Cormack et al., 2009) provides a simple, effective, and parameter-light method for combining ranked lists from different retrieval systems. The formula RRF(d) = \(\sum_{r \in R} \frac{1}{k + r(d)}\), where \(k\) is a constant (typically 60) and \(r(d)\) is the rank of document \(d\) in result list \(r\), has been shown to match or exceed more complex fusion methods across diverse benchmarks.

Recent hybrid retrieval systems combine sparse (BM25) and dense (bi-encoder) retrievers (Ma et al., 2023), but the addition of graph-based retrieval as a third modality — leveraging entity co-occurrence networks — remains underexplored in production systems. GraphRAG (Edge et al., 2024) explores graph-augmented retrieval for language model generation but does not integrate keyword and vector modalities into a unified fusion framework.

### 2.3 AI Governance Frameworks

The NIST AI Risk Management Framework (NIST AI 100-1, 2023) establishes four core functions — Govern, Map, Measure, and Manage — for responsible AI system design. FedRAMP (Federal Risk and Authorization Management Program) specifies security baselines for cloud services deployed in federal environments, with the High baseline requiring stringent controls including AU-2 (audit events), SC-28 (encryption at rest), SC-8 (transport security), and AC-2/AC-6 (access control).

To our knowledge, no existing open-source document ingestion system implements these frameworks as architectural constraints with traceable control-to-code mappings.

---

## 3. Truth-Value Classification

### 3.1 Epistemological Foundation

We observe that enterprise documents occupy distinct positions on an epistemic stability spectrum. At one extreme, technical standards, regulatory specifications, and engineering manuals represent *immutable truth* — knowledge that, once published, maintains its authority and relevance indefinitely (or until formally superseded by a new revision). At the other extreme, telemetry logs, sensor readings, and operational metrics represent *operational pulse* — data whose relevance decays rapidly as newer data supersedes it. Between these poles lies *ephemeral stream* content — emails, meeting notes, slide decks, and wiki pages — whose relevance decays at a moderate rate as organizational context evolves.

This observation motivates a formal classification:

**Definition 1 (Truth-Value Classification).** Let \(\mathcal{D}\) be the set of all documents in an enterprise corpus. We define a classification function \(\phi: \mathcal{D} \rightarrow \{A, B, C\}\) that maps each document to one of three epistemic classes:

- **Class A (Immutable Truth):** Documents whose content represents stable, authoritative knowledge with minimal temporal decay. Decay rate \(\lambda_A = 0.01\).
- **Class B (Ephemeral Stream):** Documents whose content represents contextual, collaborative knowledge with moderate temporal decay. Decay rate \(\lambda_B = 0.50\).
- **Class C (Operational Pulse):** Documents whose content represents transient operational data with rapid temporal decay. Decay rate \(\lambda_C = 0.90\).

The decay rate \(\lambda\) governs a time-dependent relevance function:

\[
\text{relevance}(d, t) = e^{-\lambda_{\phi(d)} \cdot (t - t_{\text{ingest}}(d))}
\]

where \(t_{\text{ingest}}(d)\) is the ingestion timestamp of document \(d\) and \(t\) is the query time.

### 3.2 Classification Mechanism

The classification function \(\phi\) operates in two phases:

**Phase 1: Extension-Based Classification.** File extension provides the primary signal. The system maintains three disjoint extension sets:

- \(E_A = \{\texttt{.pdf}, \texttt{.scidoc}\}\)
- \(E_B = \{\texttt{.pptx}, \texttt{.docx}, \texttt{.doc}, \texttt{.eml}, \texttt{.msg}, \texttt{.html}, \texttt{.md}, \texttt{.txt}\}\)
- \(E_C = \{\texttt{.csv}, \texttt{.parquet}, \texttt{.json}, \texttt{.jsonl}, \texttt{.xlsx}, \texttt{.log}\}\)

**Phase 2: Keyword Escalation.** Documents initially classified as Class B undergo keyword analysis. If the filename contains any term from a curated set of truth-indicating keywords \(K_T = \{\text{manual}, \text{spec}, \text{standard}, \text{iso}, \text{safety}, \text{protocol}, \text{nist}, \text{fedramp}, \ldots\}\), the document is *escalated* to Class A. This captures the common enterprise pattern where authoritative content is authored in collaborative formats (e.g., `nist-800-53-controls.docx`).

Formally:

\[
\phi(d) = \begin{cases}
A & \text{if } \text{ext}(d) \in E_A \\
C & \text{if } \text{ext}(d) \in E_C \\
A & \text{if } \text{ext}(d) \in E_B \wedge \exists k \in K_T : k \subseteq \text{name}(d) \\
B & \text{otherwise}
\end{cases}
\]

### 3.3 Engine Routing

Classification determines extraction engine selection. Each class is associated with an engine optimized for its document type:

| Class | Engine | Rationale |
|:------|:-------|:----------|
| A | IBM Docling | High-fidelity layout analysis, TableFormer table reconstruction, bounding box coordinate preservation for provenance |
| B | Unstructured.io | Semantic chunking with header-based splitting, element type detection (title, narrative, table), cross-format support |
| C | Pandas | Native structured data handling with column preservation, numeric precision, and row-level chunking |

The routing includes a fallback mechanism: if the Class A engine (Docling) is unavailable or fails, the system degrades to the Class B engine (Unstructured) for resilience, preserving the classification metadata while accepting reduced extraction fidelity.

### 3.4 Sensitivity Classification

Orthogonal to truth-value classification, each document receives a sensitivity classification aligned with NIST SP 800-60 impact levels:

- **High:** Documents whose filenames contain indicators of sensitive content (credentials, PII, PHI, CUI). High-sensitivity documents automatically set `requires_encryption = true`, triggering AES-256 encryption at rest per FedRAMP SC-28.
- **Moderate:** Documents containing proprietary, internal, confidential, or draft content.
- **Low:** All other documents.

Additionally, documents are tagged with applicable compliance frameworks (NIST AI RMF, FedRAMP, ISO 27001, HIPAA) and data categories (PII, PHI, CUI, PCI, PROPRIETARY, SAFETY) based on filename keyword detection. These tags propagate to every extracted chunk, enabling downstream filtering by compliance requirement.

### 3.5 Provenance Enrichment

Every chunk extracted from a classified document is enriched with a comprehensive metadata envelope:

```
ChunkMetadata {
    provenance_id:       "{class_prefix}-{uuid}"
    data_class:          "immutable_truth" | "ephemeral_stream" | "operational_pulse"
    source_file:         filename
    ingested_at:         ISO 8601 timestamp
    decay_rate:          λ ∈ {0.01, 0.50, 0.90}
    sensitivity_level:   "high" | "moderate" | "low"
    data_categories:     ["pii", "phi", "cui", ...]
    compliance_frameworks: ["NIST AI RMF", "FedRAMP", ...]
    user_id:             ingesting user
    tenant_id:           organizational tenant
    project_id:          optional project scope
    access_level:        "private" | "team" | "project" | "tenant"
    acl_groups:          ["engineering", "security", ...]
}
```

This metadata envelope satisfies NIST AI RMF MAP 1.5 (provenance and boundary preservation) and MANAGE 2.3 (classification-driven governance) by construction.

---

## 4. TriSearch: Triple-Modality Retrieval

### 4.1 Architecture

TriSearch is a retrieval architecture that executes three search modalities in parallel against a shared PostgreSQL datastore and fuses their results into a single ranked list.

The three modalities are:

1. **Keyword Search (KW):** Leverages PostgreSQL's built-in full-text search infrastructure. At ingestion time, chunk text is indexed into a `tsvector` column via `to_tsvector('english', text)`. At query time, the search query is parsed into a `tsquery` via `plainto_tsquery('english', query)`, and results are ranked by `ts_rank()`. This modality excels at exact-term matching, boolean queries, and retrieval of content containing specific identifiers, error codes, or regulatory control numbers.

2. **Vector Search (VEC):** Leverages pgvector for dense embedding similarity. At ingestion time, chunk text is embedded via Azure OpenAI's `text-embedding-ada-002` model into 1536-dimensional vectors stored in a `vector(1536)` column. At query time, the query is embedded using the same model, and results are ranked by cosine similarity via pgvector's `<=>` operator. This modality excels at semantic retrieval — finding conceptually related content even when surface-level terminology differs.

3. **Graph Knowledge Search (GK):** Leverages a property graph built during ingestion (Section 4.2). At query time, the system finds graph nodes whose labels match the query via PostgreSQL trigram similarity (`similarity()` function, threshold > 0.3), traverses edges to discover connected entities, and returns chunks from documents linked to the matched and connected nodes. This modality excels at discovering documents connected through entity relationships that neither keyword nor vector search would surface.

### 4.2 Knowledge Graph Construction

The graph knowledge modality depends on a property graph constructed during the ingestion pipeline. The construction proceeds as follows:

**Step 1: Named Entity Recognition.** Chunk text is processed through spaCy's `en_core_web_sm` model. Entities shorter than three characters are filtered. Text is limited to 5,000 characters per chunk for computational efficiency.

**Step 2: Node Upsert.** Each unique entity (deduplicated by lowercase-normalized label) becomes a node in the graph. Nodes carry the entity label, spaCy entity type (PERSON, ORG, GPE, DATE, LAW, PRODUCT, EVENT), an array of source document IDs, and a tenant isolation identifier. If a node with the same label and type already exists, the source document is appended to its `document_ids` array via PostgreSQL's `array_append()`.

**Step 3: Edge Creation.** Edges represent co-occurrence between entities within the same document. A sliding window of five entities generates edges between nearby entities. Repeated co-occurrences across multiple documents increment an edge weight counter, producing a weighted co-occurrence graph.

**Step 4: Document Linking.** Every node maintains a `document_ids` array linking entities back to their source documents. This bidirectional link — from documents to entities via NER, and from entities back to documents via `document_ids` — enables the graph search to discover documents related to a query entity even when the query terms do not appear in those documents' text.

The graph is stored entirely within PostgreSQL using two tables (`graph_nodes` and `graph_edges`) with JSONB `properties` columns for extensibility. The `pg_trgm` extension enables trigram-based fuzzy matching for entity search. This design avoids the operational complexity of a dedicated graph database while retaining the query patterns necessary for entity-relationship traversal.

### 4.3 Reciprocal Rank Fusion

When executing a full TriSearch query, results from all three modalities are fused using Reciprocal Rank Fusion (RRF) (Cormack et al., 2009).

For each chunk \(c\) appearing at rank \(r_i\) in the \(i\)-th result list, the RRF score is computed as:

\[
\text{RRF}(c) = \sum_{i=1}^{3} \frac{1}{k + r_i(c)}
\]

where \(k = 60\) is a constant that prevents top-ranked items from dominating the fused score. Chunks not appearing in a given result list contribute zero to the sum from that modality.

The final ranking sorts all chunks by accumulated RRF score in descending order. This approach has several desirable properties:

- **Parameter-light:** Only the constant \(k\) requires tuning, and the default value of 60 has been shown to be robust across diverse retrieval tasks.
- **Score-agnostic:** RRF operates on ranks, not raw scores, eliminating the need to normalize incompatible score distributions across modalities (BM25 scores, cosine similarities, and fixed graph scores).
- **Modality-balanced:** Each modality contributes proportionally to the fused ranking, preventing a single high-confidence modality from overwhelming the others.

**Example.** Consider a chunk appearing at rank 1 in keyword results, rank 3 in vector results, and rank 5 in graph results:

\[
\text{RRF} = \frac{1}{60+1} + \frac{1}{60+3} + \frac{1}{60+5} = 0.0164 + 0.0159 + 0.0154 = 0.0477
\]

A chunk appearing at rank 1 in only a single modality would score \(\frac{1}{61} = 0.0164\), significantly lower than a chunk with moderate ranks across all three modalities. This rewards breadth of evidence across retrieval paradigms.

### 4.4 Modality Degradation

TriSearch is designed for graceful degradation. If Azure OpenAI embeddings are not configured, vector search is automatically disabled and TriSearch operates on keyword + graph only. If spaCy is not available, graph search returns empty results and TriSearch operates on keyword + vector (or keyword only). The `SearchResponse` model always reports per-modality result counts (`keyword_count`, `vector_count`, `graph_count`), enabling clients to understand which modalities contributed to a given result set — satisfying NIST AI RMF MEASURE 2.1 (search quality auditability).

---

## 5. Resource Access Policy

### 5.1 Security Model

The Document Ingestion Router implements a *defense-in-depth* security model with four isolation layers, each represented in the `SecurityContext` injected into every authenticated request:

**Layer 1: Tenant Isolation (Mandatory).** Every data record — documents, chunks, graph nodes, graph edges, connectors — carries a `tenant_id` field. Tenant isolation is enforced at the SQL query level via a mandatory `WHERE tenant_id = :ctx_tenant_id` clause. This filter is applied unconditionally, regardless of user role, and cannot be bypassed even by administrators. Cross-tenant data leakage is prevented by construction.

**Layer 2: User Identity and RBAC.** Users are assigned roles (Admin, Analyst, PM, Viewer, Developer, Agent) that govern access to specific capabilities. Administrators have full access within their tenant. System-ingested resources (documents ingested programmatically with `user_id = "system"`) are accessible to Admins, Analysts, and PMs.

**Layer 3: Project Scope.** Resources can be scoped to a project via `project_id`. When `access_level = "project"`, only users with a matching `project_id` in their security context can access the resource.

**Layer 4: ACL Groups.** Resources can be scoped to teams via `acl_groups`, which are populated from the OIDC `groups` claim (e.g., "engineering", "security", "Dept:Finance"). When `access_level = "team"`, access requires at least one overlapping group between the user's context and the resource's ACL groups.

### 5.2 Access Level Hierarchy

The `access_level` field on each resource governs the authorization logic:

| Level | Access Rule |
|:------|:-----------|
| `private` | Only the resource owner (`user_id` match) |
| `team` | Owner + users sharing an `acl_groups` entry |
| `project` | Owner + users sharing a `project_id` |
| `tenant` | All authenticated users within the same tenant |

Evaluation proceeds from most restrictive to least restrictive, with the owner always having access to their own resources. This hierarchical model supports diverse enterprise patterns: individual work products (`private`), departmental collaboration (`team`), cross-functional projects (`project`), and organization-wide knowledge bases (`tenant`).

### 5.3 SQL-Level Enforcement

The `ResourceAccessPolicy.build_query_filter()` method applies access control at the SQL level, before pagination, preventing data leakage through result set manipulation:

```python
# MANDATORY: Tenant isolation (always applied)
query = query.where(model.tenant_id == ctx.tenant_id)

# Admin override within tenant
if Role.ADMIN in ctx.roles:
    return query

# Non-admin: composite access level filter
conditions = [
    model.user_id == ctx.user_id,           # Own resources
    model.access_level == "tenant",          # Tenant-wide resources
]
if can_access_system_resources(ctx):
    conditions.append(model.user_id == "system")
if ctx.project_id:
    conditions.append(and_(model.access_level == "project",
                           model.project_id == ctx.project_id))
if ctx.groups:
    conditions.append(and_(model.access_level == "team",
                           model.acl_groups.overlap(ctx.groups)))

query = query.where(or_(*conditions))
```

This query-level enforcement pattern ensures that regardless of the resource type (Document, ChunkRecord, GraphNode, ConnectorConfig), the same security semantics are applied uniformly. The policy also provides a `filter_accessible_resources()` method for post-query filtering in non-SQL scenarios (e.g., graph traversals returning dictionaries).

### 5.4 Audit Trail

Every request generates a structured audit event containing:

```json
{
    "event_type": "resource.ingest | resource.search | graph.query | ...",
    "timestamp": "ISO 8601",
    "user_id": "...",
    "tenant_id": "...",
    "project_id": "...",
    "session_id": "...",
    "request_id": "...",
    "action": "ingest | search | query | ...",
    "resource": "document_id",
    "resource_type": "document | chunk | graph_node | ...",
    "outcome": "success | failure | denied",
    "details": { ... },
    "ip_address": "...",
    "user_agent": "..."
}
```

The audit system implements FedRAMP AU-2 (auditable events) and NIST AI RMF MANAGE 4.2 (audit trails). All events are emitted as structured JSON, compatible with SIEM integration via Azure Monitor, OpenTelemetry, or any JSON-based log aggregation pipeline. The `@audited` decorator enables function-level audit instrumentation with zero boilerplate.

---

## 6. System Architecture

### 6.1 Pipeline Overview

The end-to-end ingestion pipeline proceeds through five stages:

```
[Source] → [Classify] → [Extract] → [Embed] → [Index]
   ↓           ↓            ↓          ↓         ↓
Connector   Class A/B/C  Docling/   Azure    KW (tsvector)
(16 types)  + Sensitivity Unstr./   OpenAI   VEC (pgvector)
                         Pandas    ada-002   GK (spaCy NER)
```

**Stage 1: Source.** Documents arrive via one of 16 enterprise connectors organized in five categories: Cloud Storage (S3, Azure Blob, GCS), Collaboration (SharePoint, Google Drive, OneDrive, Confluence), Ticketing (ServiceNow, Jira, GitHub), Messaging (Slack, Teams, Email), and Data/Integration (Database, Webhooks, Local Upload). Each connector implements a unified interface: `connect()`, `list_documents()`, `fetch_document()`, and `disconnect()`.

**Stage 2: Classify.** The Document Ingestion Router assigns truth-value classification (Class A/B/C), sensitivity level (High/Moderate/Low), data categories (PII, PHI, CUI, etc.), and applicable compliance frameworks based on file extension and filename keyword analysis.

**Stage 3: Extract.** The classified document is routed to the appropriate engine. IBM Docling processes Class A documents with layout analysis and table reconstruction. Unstructured.io processes Class B documents with semantic chunking. Pandas processes Class C documents with native tabular handling. Each engine produces a list of `Chunk` objects with structured metadata.

**Stage 4: Embed.** If Azure OpenAI is configured, each chunk's text is embedded into a 1536-dimensional vector via the `text-embedding-ada-002` model. Embeddings are stored in a pgvector `vector(1536)` column for vector search.

**Stage 5: Index.** Chunks are persisted to PostgreSQL with full-text search indexing (tsvector), vector embeddings (pgvector), and knowledge graph construction (spaCy NER entity extraction, node/edge creation). All three search modalities are indexed simultaneously during ingestion.

### 6.2 Durable Execution

For large-scale or long-running ingestion tasks, the system provides Temporal workflow orchestration. The `IngestionWorkflow` decomposes the pipeline into five activities (classify, extract, embed, build graph, persist), each with independent retry policies (exponential backoff, 3 maximum attempts) and timeout configurations (1 minute to 30 minutes depending on activity complexity). This ensures that a transient failure in embedding generation, for example, does not require re-extraction of the entire document.

### 6.3 Technology Stack

| Layer | Technology | Justification |
|:------|:-----------|:-------------|
| Language | Python 3.11 | Ecosystem breadth (NLP, ML, data processing) |
| Framework | FastAPI + Uvicorn | Async-native, OpenAPI auto-generation, type-safe |
| Database | PostgreSQL 16 + pgvector + pg_trgm | Unified store for relational, vector, full-text, and graph data |
| Embeddings | Azure OpenAI (text-embedding-ada-002) | 1536-dim dense embeddings, Azure Gov compatible |
| NER | spaCy (en_core_web_sm) | Fast, accurate named entity recognition |
| Workflows | Temporal | Durable execution with retry, visibility, and versioning |
| Memory | Zep | Episodic memory management for session context |
| Configuration | Pydantic Settings | Type-safe, environment-variable-based configuration |
| Containerization | Docker Compose (6 services) | Reproducible, portable deployment |
| Infrastructure | Azure Bicep (commercial + GovCloud) | FedRAMP-authorized cloud platform |

A notable architectural decision is the use of PostgreSQL as a *unified data substrate* for all four data modalities: relational records (documents, chunks), full-text search (tsvector), vector similarity (pgvector), and property graph (nodes/edges with JSONB properties and trigram similarity). This eliminates the operational complexity of maintaining separate Elasticsearch, Pinecone/Weaviate, and Neo4j instances, while PostgreSQL 16's mature extension ecosystem provides competitive performance for each modality at enterprise scale.

---

## 7. Connector Architecture

### 7.1 Unified Interface

All 16 connectors implement a `BaseConnector` abstract class with four methods:

```python
class BaseConnector(ABC):
    async def connect(self) -> bool: ...
    async def list_documents(self) -> List[Dict[str, Any]]: ...
    async def fetch_document(self, doc_id: str, dest_path: str) -> str: ...
    async def disconnect(self): ...
```

This uniform interface enables the ingestion pipeline to treat all data sources identically: connect, enumerate available documents, fetch individual documents to a local staging area, and route them through the classification/extraction/indexing pipeline.

### 7.2 Connector Categories

The 16 connectors span five categories, collectively covering the major enterprise data source patterns:

**Cloud Storage (3):** AWS S3, Azure Blob Storage, and Google Cloud Storage. These connectors poll object stores for documents, supporting prefix-based filtering for selective ingestion.

**Collaboration (4):** SharePoint, Google Drive, OneDrive, and Confluence. These connectors authenticate via OAuth2 or API keys and enumerate document libraries, folders, or wiki spaces.

**Ticketing (3):** ServiceNow, Jira, and GitHub. These connectors sync tickets, issues, knowledge base articles, and pull requests as structured JSON documents.

**Messaging (3):** Slack, Microsoft Teams, and Email (IMAP). These connectors archive channel histories and mailbox contents for organizational knowledge capture.

**Data & Integration (3):** Database (SQL/NoSQL via DSN), Webhooks (push-based real-time ingestion), and Local file upload.

### 7.3 Security Inheritance

Connectors inherit the security context of their configuring user. When a connector syncs documents, each ingested document inherits the connector's `tenant_id`, `project_id`, `access_level`, and `acl_groups`. This ensures that documents ingested from a departmental SharePoint library, for example, are automatically scoped to the appropriate team and project.

---

## 8. Compliance Mapping

The Document Ingestion Router maintains traceable mappings from regulatory controls to implementation artifacts:

### 8.1 NIST AI RMF

| Control | Function | Implementation |
|:--------|:---------|:---------------|
| MAP 1.5 | Context and Boundaries | Provenance ID, source file, ingestion timestamp, entity relationships on every chunk |
| MANAGE 2.3 | Data Governance | Truth-value classification determines engine, decay rate, and policy application |
| MEASURE 2.1 | Data Quality | Classification confidence scores, structured chunk metadata, per-modality search counts |
| GOVERN 1.1 | Policies | Pydantic-validated configuration, FIPS mode toggle, encryption-at-rest flag |
| GOVERN 1.2 | Accountability | Structured audit logging on every request with user, tenant, and resource identification |
| MANAGE 4.2 | Audit | Comprehensive audit event types: security, resource, graph, agent, connector, admin, system |

### 8.2 FedRAMP High

| Control | Baseline | Implementation |
|:--------|:---------|:---------------|
| AU-2 | Audit Events | AuditMiddleware logs every API request with timestamp, method, path, IP, status, duration |
| SC-28 | Encryption at Rest | High-sensitivity documents trigger `requires_encryption = true`; AES-256 support configurable |
| SC-8 | Transport Security | TLS 1.3 required in production; FIPS 140-2 module support configurable |
| AC-2 | Access Control | Tenant isolation mandatory on all records; RBAC with six defined roles |
| AC-6 | Least Privilege | Row-level security via `acl_groups`; access level hierarchy (private → team → project → tenant) |

### 8.3 NIST SP 800-60

Sensitivity classification (High/Moderate/Low) is applied automatically based on filename analysis, with data category tagging (PII, PHI, CUI, PCI, PROPRIETARY, SAFETY) enabling downstream compliance filtering.

---

## 9. Discussion

### 9.1 Limitations and Future Work

**Classification Granularity.** The current truth-value classification relies primarily on file extension and filename keywords. Future work should incorporate content-based classification using lightweight language models to analyze document text, improving accuracy for documents whose filenames do not reflect their epistemic character.

**Graph Sophistication.** The current knowledge graph uses co-occurrence as the sole relationship type. Richer relationship extraction (e.g., "authored by," "supersedes," "references") via relation extraction models would enable more expressive graph queries and improve the graph search modality's precision.

**Decay Function Calibration.** The exponential decay rates (0.01, 0.50, 0.90) are heuristically assigned. Empirical calibration against enterprise document usage patterns — measuring how actual access frequency correlates with document age across classes — would enable more accurate relevance weighting.

**Embedding Model Selection.** The system currently uses `text-embedding-ada-002`. Evaluation of more recent embedding models (e.g., `text-embedding-3-large` with configurable dimensionality) and domain-specific fine-tuned embeddings may improve retrieval quality for specialized corpora.

**Scalability.** While PostgreSQL provides a pragmatic unified data substrate at moderate scale, organizations ingesting millions of documents may require partitioning strategies (e.g., by tenant and date range), read replicas, or migration of the vector search layer to a dedicated index (e.g., pgvector with HNSW indexes, or an external vector database).

### 9.2 Implications for AI Data Pipelines

The truth-value classification paradigm has broader implications for AI system design. As retrieval-augmented generation (RAG) becomes a standard architecture for grounding language model outputs in enterprise knowledge, the quality and governance of the retrieval layer become critical. Documents of different epistemic classes should receive different treatment not only during ingestion and search but also during generation: an LLM should weight a Class A technical specification more heavily than a Class C operational log when constructing a compliance-related answer.

Similarly, the Resource Access Policy model demonstrates that enterprise-grade RAG systems must enforce access control at the retrieval level, not merely at the application level. If a user does not have access to a document, that document's chunks must not appear in their retrieval results — regardless of semantic relevance. SQL-level enforcement, as implemented in this system, provides this guarantee by construction.

### 9.3 The Context Ecology Vision

The Document Ingestion Router is designed as a component of the Context Ecology (ctxEco) platform — a broader vision for AI systems that are recursively self-aware, maintain episodic and semantic memory, and evolve their understanding through continuous ingestion. In this vision, the ingestion router serves as the "sensory organ" of the ecology: transforming raw enterprise documents into classified, indexed, and governed knowledge chunks that agents (Marcus, Elena, Sage) can query, reason over, and synthesize into actionable intelligence.

---

## 10. Conclusion

We have presented the Document Ingestion Router, an architecture for enterprise document processing that unifies truth-value classification, triple-modality retrieval, and defense-in-depth access control. The truth-value classification taxonomy (Immutable Truth, Ephemeral Stream, Operational Pulse) provides an epistemic foundation for differentiated document governance, while TriSearch's fusion of keyword, vector, and graph knowledge search via Reciprocal Rank Fusion delivers comprehensive retrieval across exact-match, semantic, and relational query types. The Resource Access Policy enforces four-layer security isolation at the SQL level, ensuring compliance with NIST AI RMF and FedRAMP High baselines by construction.

The system is implemented as an open-source FastAPI/MCP server with 16 enterprise connectors, Temporal durable workflow orchestration, and Zep memory integration, deployable on Azure commercial and GovCloud environments. It demonstrates that compliance-aware AI data pipelines need not sacrifice developer ergonomics or architectural simplicity — PostgreSQL, with its mature extension ecosystem, provides a unified data substrate for relational, full-text, vector, and graph workloads, eliminating the operational complexity of multi-database architectures.

As enterprise AI systems increasingly operate in regulated environments, we believe that epistemic classification, multi-modal retrieval, and construction-time compliance guarantees will become standard architectural requirements. The Document Ingestion Router provides a concrete, open-source reference implementation for this emerging paradigm.

---

## References

Auer, C., et al. (2023). Docling Technical Report. IBM Research. arXiv:2408.09869.

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal rank fusion outperforms condorcet and individual rank learning methods. *Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval*, 758-759.

Edge, D., et al. (2024). From Local to Global: A Graph RAG Approach to Query-Focused Summarization. Microsoft Research. arXiv:2404.16130.

Karpukhin, V., et al. (2020). Dense Passage Retrieval for Open-Domain Question Answering. *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, 6769-6781.

Ma, X., et al. (2023). Fine-Tuning LLaMA for Multi-Stage Text Retrieval. arXiv:2310.08319.

National Institute of Standards and Technology. (2023). Artificial Intelligence Risk Management Framework (AI RMF 1.0). NIST AI 100-1.

National Institute of Standards and Technology. (2008). Guide for Mapping Types of Information and Information Systems to Security Categories. NIST SP 800-60 Vol. 1 Rev. 1.

Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333-389.

---

*This paper describes the Document Ingestion Router, an open-source component of the Context Ecology (ctxEco) platform by derek brent moore. The software is available under the MIT license at https://github.com/derekbmoore/documentIngestionRouter.*
