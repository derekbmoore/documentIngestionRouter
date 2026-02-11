---
layout: default
title: Home
nav_order: 1
description: "Intelligent document classification, extraction, and TriSearch™ indexing for enterprise workloads."
permalink: /
---

# Document Ingestion Router

{: .fs-9 }

Intelligent document classification, extraction, and TriSearch™ indexing for enterprise workloads.
{: .fs-6 .fw-300 }

Part of the [Context Ecology (ctxEco)](https://github.com/derekbmoore) platform by **Zimax Networks LC**.
{: .fs-4 .fw-300 }

[Get Started](/documentIngestionRouter/getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/derekbmoore/documentIngestionRouter){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## What It Does

The Document Ingestion Router is a standalone, open-source **MCP server** that classifies documents by their "truth value," routes them to specialized extraction engines, and indexes them for **TriSearch™** — a unified search across keyword, vector, and knowledge graph modalities.

### Key Capabilities

| Feature | Description |
|:--------|:------------|
| **Truth-Value Classification** | Class A (Immutable), B (Ephemeral), C (Operational) |
| **3 Extraction Engines** | IBM Docling, Unstructured.io, Pandas |
| **TriSearch™** | Keyword + Vector + Graph fused via Reciprocal Rank Fusion |
| **Knowledge Graph** | spaCy NER → PostgreSQL property graph |
| **16 Connectors** | S3, Azure Blob, GCS, SharePoint, and 12 more |
| **Compliance** | NIST AI RMF, FedRAMP High, NIST SP 800-60 |

---

## Architecture

```mermaid
flowchart LR
    subgraph Sources["16 Connectors"]
        S3[S3] 
        Blob[Azure Blob]
        SP[SharePoint]
        More[+ 13 more]
    end

    subgraph Router["Document Ingestion Router"]
        Classify["Classify\n(A / B / C)"]
        Docling["Docling\n(Class A)"]
        Unstructured["Unstructured\n(Class B)"]
        Pandas["Pandas\n(Class C)"]
    end

    subgraph Index["TriSearch™ Index"]
        KW["Keyword\n(tsvector)"]
        VEC["Vector\n(pgvector)"]
        GK["Graph\n(Gk NER)"]
    end

    Sources --> Classify
    Classify --> Docling
    Classify --> Unstructured
    Classify --> Pandas
    Docling --> Index
    Unstructured --> Index
    Pandas --> Index
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/derekbmoore/documentIngestionRouter.git
cd documentIngestionRouter

# Configure
cp .env.example .env

# Run
docker compose up -d

# Upload a document
curl -X POST http://localhost:8082/api/v1/ingest \
  -F "file=@my-document.pdf"

# Search
curl "http://localhost:8082/api/v1/search?q=compliance&mode=trisearch"
```

Open [http://localhost:8082/docs](http://localhost:8082/docs) for the interactive Swagger UI.

---

## License

MIT — see [LICENSE](https://github.com/derekbmoore/documentIngestionRouter/blob/main/LICENSE).

Commercially supported by [Zimax Networks LC](https://zimax.net). Available on the [Azure Marketplace](https://azuremarketplace.microsoft.com).
