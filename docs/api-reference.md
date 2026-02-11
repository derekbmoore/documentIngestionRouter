---
layout: default
title: API Reference
nav_order: 5
---

# API Reference

{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Base URL**: `http://localhost:8082`
**API Prefix**: `/api/v1`
**Interactive Docs**: [http://localhost:8082/docs](http://localhost:8082/docs) (Swagger UI)

---

## Health

### `GET /health`

Returns service status.

```json
{
  "status": "healthy",
  "service": "Document Ingestion Router",
  "version": "1.0.0"
}
```

### `GET /ready`

Readiness probe — checks database connectivity.

```json
{
  "ready": true,
  "database": "connected"
}
```

---

## Ingestion

### `POST /api/v1/ingest`

Upload and ingest a document. The pipeline: classify → extract → embed → index → build graph.

**Request** (multipart/form-data):

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `file` | File | ✅ | Document to ingest |
| `force_class` | string | | Override classification: `immutable_truth`, `ephemeral_stream`, `operational_pulse` |
| `tenant_id` | string | | Tenant isolation ID |
| `user_id` | string | | User who uploaded |

**Example:**

```bash
curl -X POST http://localhost:8082/api/v1/ingest \
  -F "file=@report.pdf" \
  -F "tenant_id=acme-corp"
```

**Response** (`IngestResult`):

```json
{
  "success": true,
  "filename": "report.pdf",
  "document_id": "a1b2c3d4e5f67890",
  "chunks_processed": 24,
  "message": "Ingested 24 chunks as immutable_truth",
  "classification": {
    "data_class": "immutable_truth",
    "reason": "Extension .pdf → technical document",
    "sensitivity_level": "low",
    "data_categories": ["internal"],
    "decay_rate": 0.01,
    "requires_encryption": false,
    "compliance_frameworks": [],
    "confidence": 0.85
  }
}
```

### `GET /api/v1/documents`

List ingested documents with optional filtering.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `tenant_id` | string | | Filter by tenant |
| `data_class` | string | | Filter by class |
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |

**Example:**

```bash
curl "http://localhost:8082/api/v1/documents?data_class=immutable_truth&limit=10"
```

---

## Search

### `GET /api/v1/search`

TriSearch™ — unified search across keyword, vector, and graph knowledge.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `q` | string | *required* | Search query |
| `mode` | string | `trisearch` | `keyword`, `vector`, `graph`, or `trisearch` |
| `tenant_id` | string | | Filter by tenant |
| `limit` | int | 20 | Max results (1–100) |

**Example:**

```bash
curl "http://localhost:8082/api/v1/search?q=fedramp+controls&mode=trisearch"
```

**Response** (`SearchResponse`):

```json
{
  "query": "fedramp controls",
  "mode": "trisearch",
  "results": [
    {
      "chunk_id": "a1b2-0003",
      "text": "FedRAMP High requires encryption at rest...",
      "score": 0.032,
      "source_file": "nist-controls.pdf",
      "data_class": "immutable_truth",
      "search_mode": "trisearch"
    }
  ],
  "total": 5,
  "keyword_count": 3,
  "vector_count": 4,
  "graph_count": 2
}
```

---

## Connectors

### `GET /api/v1/connectors/available`

List all 16 available connector types.

```json
{
  "connectors": [
    {
      "kind": "S3",
      "category": "cloud_storage",
      "icon": "🪣",
      "description": "Poll AWS S3 buckets for documents",
      "supported_extensions": [".pdf", ".docx", ".xlsx", ".csv", ".json", ".txt", ".pptx"],
      "requires_oauth": false,
      "requires_api_key": true
    }
  ],
  "total": 16
}
```

### `POST /api/v1/connectors`

Register a new connector.

**Request** (`ConnectorConfig`):

```json
{
  "name": "Production S3 Bucket",
  "kind": "S3",
  "config": {
    "access_key": "AKIA...",
    "secret_key": "...",
    "bucket": "my-documents",
    "region": "us-east-1"
  },
  "default_class": "ephemeral_stream"
}
```

### `GET /api/v1/connectors`

List configured connectors. Optional `tenant_id` filter.

### `POST /api/v1/connectors/{connector_id}/test`

Test connectivity for a configured connector.

```json
{"status": "success", "connector_id": "abc123"}
```

---

## Graph Knowledge

### `GET /api/v1/graph/query`

Traverse the knowledge graph from an entity.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `entity` | string | *required* | Starting entity to search |
| `depth` | int | 2 | Traversal depth (1–5) |
| `tenant_id` | string | | Filter by tenant |
| `limit` | int | 50 | Max results (1–200) |

**Example:**

```bash
curl "http://localhost:8082/api/v1/graph/query?entity=NIST&depth=2"
```

**Response** (`GraphQueryResult`):

```json
{
  "nodes": [
    {"id": "n001", "label": "NIST", "entity_type": "ORG", "properties": {}},
    {"id": "n002", "label": "FedRAMP", "entity_type": "ORG", "properties": {}}
  ],
  "edges": [
    {"id": "e001", "source_id": "n001", "target_id": "n002",
     "relationship": "co_occurs", "weight": 3.0}
  ],
  "paths": []
}
```

### `GET /api/v1/graph/stats`

Knowledge graph statistics.

```json
{
  "total_nodes": 1234,
  "total_edges": 5678,
  "entity_types": [
    {"type": "ORG", "count": 450},
    {"type": "PERSON", "count": 320},
    {"type": "GPE", "count": 280}
  ]
}
```
