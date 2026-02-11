# Document Ingestion Router

**An MCP Server for intelligent document ingestion, classification, and TriSearch™ indexing.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![NIST AI RMF](https://img.shields.io/badge/NIST-AI%20RMF-blue)](https://www.nist.gov/artificial-intelligence/risk-management-framework)
[![FedRAMP High](https://img.shields.io/badge/FedRAMP-High-green)](https://www.fedramp.gov/)

> Part of the **Context Ecology (ctxEco)** platform by [Zimax Networks LC](https://zimax.net)  
> Open-source (MIT) · Commercially supported MCP server for Azure Marketplace

---

## What It Does

The Document Ingestion Router classifies documents by **truth value**, routes them through specialized extraction engines, and indexes them via **TriSearch™** — a fusion of keyword, vector, and graph knowledge search.

### Classification System

| Class | Truth Value | Engine | Decay Rate | Examples |
|-------|-------------|--------|------------|----------|
| **A** | Immutable Truth | IBM Docling | 0.01 | PDFs, manuals, specs, standards |
| **B** | Ephemeral Stream | Unstructured.io | 0.50 | Emails, slides, docs, wikis |
| **C** | Operational Pulse | Pandas | 0.90 | CSV, JSON, logs, telemetry |

### 16 Enterprise Connectors

| Category | Connectors |
|----------|------------|
| Cloud Storage | AWS S3, Azure Blob, Google Cloud Storage |
| Collaboration | SharePoint, Google Drive, OneDrive, Confluence |
| Ticketing | ServiceNow, Jira, GitHub |
| Messaging | Slack, Microsoft Teams, Email (EML/MSG) |
| Data & Integration | Database (SQL/NoSQL), Webhooks |
| Local | Direct file upload |

### TriSearch™

- **Keyword**: PostgreSQL full-text search (`tsvector`/`tsquery`)
- **Vector**: `pgvector` cosine similarity with Azure OpenAI embeddings
- **Graph Knowledge (Gk)**: Entity extraction → property graph → traversal queries

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   MCP Server (API)                   │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ Classify │→ │ Extract  │→ │ Index (TriSearch™) │ │
│  │ A / B / C│  │ Engine   │  │ KW + Vec + Graph   │ │
│  └─────────┘  └──────────┘  └────────────────────┘ │
├─────────────────────────────────────────────────────┤
│  16 Connectors │ Temporal Workflows │ Zep Memory    │
├─────────────────────────────────────────────────────┤
│  PostgreSQL + pgvector │ NIST AI RMF │ FedRAMP High │
└─────────────────────────────────────────────────────┘
```

---

## Security

The router implements a **Defense-in-Depth** security model aligned with **NIST AI RMF** and **FedRAMP High**.

1. **4-Layer Context**:
   - **User Identity** (OIDC + RBAC)
   - **Tenant Isolation** (Data segregation)
   - **Project Scope** (Optional isolation)
   - **ACL Groups** (Team-based access)

2. **Resource Access Policy (RAP)**:
   - Unified SQL-level filtering for all resources (Docs, Chunks, Graph).
   - Access Levels: `private`, `team`, `project`, `tenant`.

3. **Audit Logging**:
   - Structured JSON logs for all access events (`resource.ingest`, `graph.query`).
   - Automated request context capture via middleware.

---

## Quick Start

```bash
# Clone
git clone https://github.com/derekbmoore/documentIngestionRouter.git
cd documentIngestionRouter

# Configure
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Launch
docker compose up -d

# Access
# API:       http://localhost:8082
# Dashboard: http://localhost:3000
# Temporal:  http://localhost:8088
```

---

## Compliance

- **NIST AI RMF**: MAP 1.5 (Boundaries), MANAGE 2.3 (Data Governance), MEASURE 2.1 (Data Quality), GOVERN 1.1 (Policies)
- **FedRAMP High**: Encryption at rest (AES-256), TLS 1.3, audit logging, FIPS 140-2 module support
- **NIST SP 800-60**: Sensitivity classification (High/Moderate/Low impact)

---

## License

MIT — See [LICENSE](LICENSE)

**Commercial support** available from [Zimax Networks LC](https://zimax.net) via Azure Marketplace.
