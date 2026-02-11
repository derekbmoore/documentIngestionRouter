---
layout: default
title: Compliance
nav_order: 9
---

# Compliance Mapping

{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Overview

The Document Ingestion Router is designed for deployment in regulated environments. It maps controls from **NIST AI RMF**, **FedRAMP High**, and **NIST SP 800-60** directly into its architecture and operations.

---

## NIST AI Risk Management Framework

The NIST AI RMF provides a structured approach to managing risks associated with AI systems. The Document Ingestion Router implements controls across four functions:

### MAP 1.5 — Context and Boundaries

{: .nist }
> Every document chunk preserves full provenance metadata: source file, ingestion timestamp, classification, decay rate, and data categories.

| Implementation | Location |
|:---------------|:---------|
| Provenance ID on every chunk | `classifier.py` — `provenance_id = f"{class}-{uuid}"` |
| Source file tracking | `ChunkMetadata.source_file` |
| Ingestion timestamps | `ChunkMetadata.ingested_at` |
| Entity relationships preserved | `knowledge.py` — document-to-entity graph |

### MANAGE 2.3 — Data Governance

{: .nist }
> Classification is the first governance step. It determines which extraction engine processes the document and what policies apply.

| Implementation | Location |
|:---------------|:---------|
| Truth-value classification (A/B/C) | `classifier.py` |
| Sensitivity classification | `_classify_sensitivity()` |
| Data category tagging | `_detect_categories()` |
| Tenant isolation | `tenant_id` on all records |
| ACL groups | `acl_groups` on chunks |

### MEASURE 2.1 — Data Quality

{: .nist }
> Extraction quality is auditable. Each engine produces chunks with structured metadata for quality assessment.

| Implementation | Location |
|:---------------|:---------|
| Classification confidence scores | `ClassificationResult.confidence` |
| Structured chunk metadata | `ChunkMetadata` model |
| Audit logging on every request | `AuditMiddleware` |
| search quality auditable | `SearchResponse` includes modality counts |

### GOVERN 1.1 — Policies

{: .nist }
> Explicit policies govern the entry point, configuration, and operational boundaries.

| Implementation | Location |
|:---------------|:---------|
| Pydantic settings validation | `config.py` |
| Environment-based configuration | `.env` / `Settings` |
| FIPS mode toggle | `settings.fips_mode` |
| Encryption-at-rest flag | `settings.encryption_at_rest` |

---

## FedRAMP High

### Audit Logging (AU-2)

Every API request is logged with:

- Timestamp (ISO 8601)
- HTTP method and path
- Client IP address
- User agent
- Response status code
- Processing duration (ms)

Implemented in `api/middleware/audit.py` as FastAPI middleware.

### Encryption at Rest (SC-28)

| Control | Implementation |
|:--------|:---------------|
| Encryption flag | Documents classified as High sensitivity set `requires_encryption = true` |
| AES-256 support | Configurable via `ENCRYPTION_AT_REST=true` |
| FIPS 140-2 | Configurable via `FIPS_MODE=true` |

### Transport Security (SC-8)

| Control | Implementation |
|:--------|:---------------|
| TLS 1.3 | Required in production (reverse proxy / Azure) |
| No plaintext secrets | All credentials via environment variables |

### Access Control (AC-2, AC-6)

| Control | Implementation |
|:--------|:---------------|
| Tenant isolation | `tenant_id` on all data models |
| Row-level security | `acl_groups` on chunks |
| Azure AD integration | Optional auth middleware |
| Managed Identity | Preferred for Azure services |

---

## NIST SP 800-60 — Data Sensitivity

Documents are automatically classified by sensitivity impact level using filename-based heuristics:

| Impact Level | Triggers | Effect |
|:-------------|:---------|:-------|
| **High** | `secret`, `credential`, `password`, `ssn`, `pii`, `phi`, `cui` | Encryption required |
| **Moderate** | `proprietary`, `internal`, `confidential`, `draft` | Standard handling |
| **Low** | Default | Standard handling |

### Data Categories

| Category | Framework | Handling |
|:---------|:----------|:---------|
| PII | NIST 800-122, GDPR | High sensitivity |
| PHI | HIPAA | High sensitivity |
| CUI | NIST 800-171 | High sensitivity |
| PCI | PCI DSS | High sensitivity |
| Safety | NIST AI RMF | Flagged |

---

## Compliance Auto-Detection

The classifier automatically detects and tags applicable compliance frameworks based on filename content:

| Keyword | Framework Tagged |
|:--------|:----------------|
| `nist` | NIST AI RMF |
| `fedramp` | FedRAMP |
| `iso` | ISO 27001 |
| `hipaa` | HIPAA |
