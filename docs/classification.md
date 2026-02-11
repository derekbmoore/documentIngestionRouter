---
layout: default
title: Classification System
nav_order: 4
---

# Classification System

{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Truth-Value Classification

Every document is classified into one of three classes based on its **truth value** — how stable and authoritative the information is over time.

| Class | Truth Value | Engine | Decay Rate | Confidence |
|:------|:------------|:-------|:-----------|:-----------|
| **A** | Immutable Truth | IBM Docling | 0.01 | 0.85 |
| **B** | Ephemeral Stream | Unstructured.io | 0.50 | 0.70 |
| **C** | Operational Pulse | Pandas | 0.90 | 0.70 |

{: .nist }
> **NIST AI RMF MANAGE 2.3** — Classification is the first governance step. It determines which extraction engine processes the document and what decay rate governs its relevance over time.

---

## File Extension Mapping

### Class A — Immutable Truth

High-fidelity documents with permanent relevance. Processed by **IBM Docling** for table extraction, layout analysis, and bounding box metadata.

| Extension | Description |
|:----------|:------------|
| `.pdf` | PDF documents |
| `.scidoc` | Scientific documents |

### Class B — Ephemeral Stream

Narrative and collaborative content with moderate decay. Processed by **Unstructured.io** for semantic chunking.

| Extension | Description |
|:----------|:------------|
| `.pptx` | PowerPoint presentations |
| `.docx`, `.doc` | Word documents |
| `.eml`, `.msg` | Email messages |
| `.html` | Web pages |
| `.md` | Markdown files |
| `.txt` | Plain text |

### Class C — Operational Pulse

Structured operational data with rapid decay. Processed by **Pandas** for native tabular handling.

| Extension | Description |
|:----------|:------------|
| `.csv` | Comma-separated values |
| `.parquet` | Apache Parquet |
| `.json`, `.jsonl` | JSON / JSON Lines |
| `.xlsx` | Excel spreadsheets |
| `.log` | Log files |

---

## Keyword Escalation

Class B files (`.docx`, `.md`, `.txt`, etc.) are **escalated to Class A** if the filename contains technical keywords indicating immutable content:

```
manual, spec, specification, standard, iso, safety, protocol, procedure,
guideline, regulation, compliance, datasheet, technical, engineering,
reference, nist, fedramp, stig, cve, policy
```

**Example**: `nist-800-53-controls.docx` → escalated from Class B to **Class A**.

---

## Sensitivity Classification (NIST SP 800-60)

In addition to truth-value classification, every document receives a **sensitivity level** based on filename analysis.

| Level | Trigger Keywords | Encryption Required |
|:------|:----------------|:-------------------|
| **High** | `secret`, `credential`, `password`, `ssn`, `pii`, `phi`, `cui` | ✅ Yes |
| **Moderate** | `proprietary`, `internal`, `confidential`, `draft` | No |
| **Low** | Default | No |

{: .fedramp }
> **FedRAMP High** — Documents classified as High sensitivity automatically set `requires_encryption = true`. AES-256 at-rest encryption is applied per FedRAMP SC-28.

---

## Data Categories

Documents are tagged with categories for compliance filtering:

| Category | Trigger | Applicable Frameworks |
|:---------|:--------|:---------------------|
| `PII` | `pii`, `ssn` in filename | NIST 800-122, GDPR |
| `PHI` | `phi`, `hipaa` in filename | HIPAA |
| `CUI` | `cui` in filename | NIST 800-171 |
| `SAFETY` | `safety` in filename | NIST AI RMF |
| `PROPRIETARY` | `proprietary` in filename | Trade secret |
| `INTERNAL` | Default | — |

---

## Decay Rates

Decay rates control how document relevance diminishes over time:

```
Class A (0.01): ████████████████████████████████ Nearly permanent
Class B (0.50): ████████████████                 Moderate decay
Class C (0.90): ████                             Rapid decay
```

Lower decay rates mean information stays relevant longer. Class A documents (standards, specifications) maintain relevance almost indefinitely, while Class C operational data (logs, telemetry) rapidly decays.

---

## Force Classification Override

You can override automatic classification when ingesting:

```bash
curl -X POST http://localhost:8082/api/v1/ingest \
  -F "file=@meeting-notes.docx" \
  -F "force_class=immutable_truth"
```

Valid values: `immutable_truth`, `ephemeral_stream`, `operational_pulse`.
