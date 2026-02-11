---
layout: default
title: Getting Started
nav_order: 3
---

# Getting Started

{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Prerequisites

| Requirement | Version |
|:------------|:--------|
| Docker & Docker Compose | 24+ |
| Git | 2.x |
| Azure OpenAI (optional) | API key for vector search |

---

## 1. Clone the Repository

```bash
git clone https://github.com/derekbmoore/documentIngestionRouter.git
cd documentIngestionRouter
```

---

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Required — Database
POSTGRES_DB=doc_ingestion
POSTGRES_USER=dir_admin
POSTGRES_PASSWORD=your_secure_password

# Optional — Azure OpenAI (enables vector search)
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

{: .nist }
> **NIST AI RMF GOVERN 1.1** — All secrets must be managed via environment variables, never committed to source control.

---

## 3. Launch the Stack

```bash
docker compose up -d
```

This starts all services:

| Service | URL |
|:--------|:----|
| API (FastAPI) | [http://localhost:8082](http://localhost:8082) |
| Swagger UI | [http://localhost:8082/docs](http://localhost:8082/docs) |
| Temporal UI | [http://localhost:8088](http://localhost:8088) |
| PostgreSQL | `localhost:5432` |
| Zep Memory | `localhost:8000` |

Verify everything is running:

```bash
curl http://localhost:8082/health
# → {"status": "healthy", "service": "Document Ingestion Router", "version": "1.0.0"}
```

---

## 4. Upload Your First Document

```bash
curl -X POST http://localhost:8082/api/v1/ingest \
  -F "file=@my-document.pdf"
```

**Response:**

```json
{
  "success": true,
  "filename": "my-document.pdf",
  "document_id": "a1b2c3d4e5f67890",
  "chunks_processed": 12,
  "message": "Ingested 12 chunks as immutable_truth",
  "classification": {
    "data_class": "immutable_truth",
    "reason": "Extension .pdf → technical document",
    "sensitivity_level": "low",
    "decay_rate": 0.01,
    "confidence": 0.85
  }
}
```

---

## 5. Search Your Documents

```bash
# TriSearch™ (keyword + vector + graph fusion)
curl "http://localhost:8082/api/v1/search?q=compliance&mode=trisearch"

# Keyword only
curl "http://localhost:8082/api/v1/search?q=compliance&mode=keyword"

# Vector only (requires Azure OpenAI)
curl "http://localhost:8082/api/v1/search?q=compliance&mode=vector"
```

---

## Next Steps

- [Classification System](/documentIngestionRouter/classification) — How documents are classified
- [API Reference](/documentIngestionRouter/api-reference) — All REST endpoints
- [Connectors](/documentIngestionRouter/connectors) — Set up data source connectors
- [Deployment](/documentIngestionRouter/deployment) — Production deployment guide
