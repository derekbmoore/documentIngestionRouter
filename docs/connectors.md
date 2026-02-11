---
layout: default
title: Connectors
nav_order: 7
---

# Enterprise Connectors

{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Overview

The Document Ingestion Router supports **16 enterprise data source connectors** across 5 categories. Each connector implements a unified interface: `connect()`, `list_documents()`, `fetch_document()`, and `disconnect()`.

---

## Connector Summary

| # | Connector | Category | Auth | Status |
|:--|:----------|:---------|:-----|:-------|
| 1 | **S3** | Cloud Storage | API Key | ✅ Implemented |
| 2 | **Azure Blob** | Cloud Storage | API Key | ✅ Implemented |
| 3 | **GCS** | Cloud Storage | API Key | ✅ Implemented |
| 4 | **SharePoint** | Collaboration | OAuth | ✅ Implemented |
| 5 | **Google Drive** | Collaboration | OAuth | ✅ Implemented |
| 6 | **OneDrive** | Collaboration | OAuth | ✅ Implemented |
| 7 | **Confluence** | Collaboration | API Key | ✅ Implemented |
| 8 | **ServiceNow** | Ticketing | API Key | ✅ Implemented |
| 9 | **Jira** | Ticketing | API Key | ✅ Implemented |
| 10 | **GitHub** | Ticketing | API Key | ✅ Implemented |
| 11 | **Slack** | Messaging | OAuth | ✅ Implemented |
| 12 | **Teams** | Messaging | OAuth | ✅ Implemented |
| 13 | **Email** | Messaging | IMAP | ✅ Implemented |
| 14 | **Database** | Data & Integration | DSN | ✅ Implemented |
| 15 | **Webhook** | Data & Integration | API Key | ✅ Implemented |
| 16 | **Local** | Local | None | ✅ Implemented |

---

## Cloud Storage

### 🪣 AWS S3

Pull documents from S3 buckets.

| Config Key | Description |
|:-----------|:------------|
| `access_key` | AWS access key ID |
| `secret_key` | AWS secret access key |
| `region` | AWS region (default: `us-east-1`) |
| `bucket` | S3 bucket name |
| `prefix` | Optional key prefix filter |

```json
{
  "name": "Production S3",
  "kind": "S3",
  "config": {
    "access_key": "AKIA...",
    "secret_key": "...",
    "bucket": "my-documents",
    "region": "us-gov-west-1"
  }
}
```

### ☁️ Azure Blob Storage

Sync from Azure Blob Storage containers.

| Config Key | Description |
|:-----------|:------------|
| `connection_string` | Azure Storage connection string |
| `container` | Blob container name |

### 🌩️ Google Cloud Storage

Sync from GCS buckets.

| Config Key | Description |
|:-----------|:------------|
| `bucket` | GCS bucket name |
| `prefix` | Optional prefix filter |

---

## Collaboration

### 📂 SharePoint

Sync from SharePoint document libraries via OAuth.

| Config Key | Description |
|:-----------|:------------|
| `site_url` | SharePoint site URL |
| `client_id` | Azure AD app client ID |
| `client_secret` | Azure AD app client secret |
| `library` | Document library name (default: `Shared Documents`) |
| `site_name` | SharePoint site name |

### 📁 Google Drive

Watch and sync Google Drive folders.

| Config Key | Description |
|:-----------|:------------|
| `credentials` | Google OAuth2 credentials (JSON) |
| `folder_id` | Drive folder ID (default: `root`) |

### ☁️ OneDrive

Sync from OneDrive personal or business.

| Config Key | Description |
|:-----------|:------------|
| `client_id` | Azure AD application ID |
| `client_secret` | Azure AD client secret |
| `tenant_id` | Azure AD tenant ID |
| `folder` | Folder path (default: `root`) |

### 📄 Confluence

Crawl Confluence spaces and pages.

| Config Key | Description |
|:-----------|:------------|
| `url` | Confluence instance URL |
| `username` | Confluence username |
| `api_token` | Confluence API token |
| `space_key` | Confluence space key |

---

## Ticketing

### 🎫 ServiceNow

Sync incidents and knowledge base articles.

| Config Key | Description |
|:-----------|:------------|
| `instance_url` | ServiceNow instance URL |
| `username` | ServiceNow username |
| `password` | ServiceNow password |
| `table` | ServiceNow table (default: `kb_knowledge`) |

### 🔷 Jira

Sync Jira issues and epics.

| Config Key | Description |
|:-----------|:------------|
| `url` | Jira instance URL |
| `username` | Jira username |
| `api_token` | Jira API token |
| `jql` | JQL query (default: `project = PROJ ORDER BY created DESC`) |

### 🐙 GitHub

Sync GitHub issues, PRs, and repository files.

| Config Key | Description |
|:-----------|:------------|
| `token` | GitHub personal access token |
| `repo` | Repository (format: `owner/repo`) |

---

## Messaging

### 💬 Slack

Archive Slack channels.

| Config Key | Description |
|:-----------|:------------|
| `token` | Slack Bot OAuth token |

### 🟦 Microsoft Teams

Archive Teams chat history.

| Config Key | Description |
|:-----------|:------------|
| `client_id` | Azure AD application ID |
| `client_secret` | Azure AD client secret |
| `tenant_id` | Azure AD tenant ID |

### 📧 Email (IMAP)

Import from IMAP mailboxes (EML/MSG/MBOX).

| Config Key | Description |
|:-----------|:------------|
| `imap_host` | IMAP server hostname |
| `username` | Email username |
| `password` | Email password |
| `folder` | Mailbox folder (default: `INBOX`) |

---

## Data & Integration

### 🗄️ Database

Execute SQL queries and ingest results.

| Config Key | Description |
|:-----------|:------------|
| `dsn` | Database connection string (SQLAlchemy format) |
| `query` | Optional custom SQL query |

### 🔗 Webhook

Receive real-time data pushes. Webhooks are **push-based** — they listen for incoming POST requests at a configured endpoint rather than polling a source.

---

## Local Upload

### 📤 Local

Direct file upload from local machine. No configuration required — files are uploaded via the `/api/v1/ingest` endpoint.

**Supported extensions**: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.csv`, `.json`, `.html`, `.md`, `.eml`, `.msg`, `.parquet`, `.log`, `.jsonl`

---

## Connector API

```bash
# List all available connector types
curl http://localhost:8082/api/v1/connectors/available

# Register a connector
curl -X POST http://localhost:8082/api/v1/connectors \
  -H "Content-Type: application/json" \
  -d '{"name": "My S3", "kind": "S3", "config": {"bucket": "docs"}}'

# List configured connectors
curl http://localhost:8082/api/v1/connectors

# Test a connector
curl -X POST http://localhost:8082/api/v1/connectors/abc123/test
```
