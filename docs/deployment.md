---
layout: default
title: Deployment
nav_order: 10
---

# Deployment Guide

{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Local Development (Docker Compose)

The fastest way to run the full stack:

```bash
cp .env.example .env
# Edit .env with your credentials
docker compose up -d
```

### Services

| Service | Image | Port | Purpose |
|:--------|:------|:-----|:--------|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | PostgreSQL + pgvector + pg_trgm |
| `zep` | `ghcr.io/getzep/zep:latest` | 8000 | Memory management layer |
| `temporal` | `temporalio/auto-setup:1.24` | 7233 | Durable workflow orchestration |
| `temporal-ui` | `temporalio/ui:2.26.2` | 8088 | Temporal workflow dashboard |
| `api` | Custom build | 8082 | FastAPI + MCP server |
| `worker` | Custom build | — | Temporal workflow worker |
| `frontend` | Custom build | 3000 | React dashboard |

### Verify

```bash
# Health check
curl http://localhost:8082/health

# Readiness (checks DB)
curl http://localhost:8082/ready

# Temporal UI
open http://localhost:8088
```

---

## Environment Variables

All configuration is via environment variables. See [`.env.example`](https://github.com/derekbmoore/documentIngestionRouter/blob/main/.env.example) for the full template.

### Required

| Variable | Description | Default |
|:---------|:------------|:--------|
| `POSTGRES_DB` | Database name | `doc_ingestion` |
| `POSTGRES_USER` | Database user | `dir_admin` |
| `POSTGRES_PASSWORD` | Database password | `changeme` |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |

### Embeddings (Optional)

| Variable | Description |
|:---------|:------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Deployment name (default: `text-embedding-ada-002`) |

### Services

| Variable | Description | Default |
|:---------|:------------|:--------|
| `ZEP_API_URL` | Zep memory service URL | `http://localhost:8000` |
| `TEMPORAL_HOST` | Temporal server address | `localhost:7233` |
| `TEMPORAL_NAMESPACE` | Temporal namespace | `default` |

### Security

| Variable | Description | Default |
|:---------|:------------|:--------|
| `AUTH_REQUIRED` | Enable Azure AD auth | `false` |
| `AZURE_AD_TENANT_ID` | Azure AD tenant ID | — |
| `AZURE_AD_CLIENT_ID` | Azure AD client ID | — |
| `FIPS_MODE` | Enable FIPS 140-2 mode | `false` |
| `ENCRYPTION_AT_REST` | Enable encryption at rest | `true` |

### Application

| Variable | Description | Default |
|:---------|:------------|:--------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `DOCLING_ENABLED` | Enable Docling engine | `true` |
| `UPLOAD_DIR` | Upload directory | `/app/uploads` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `500` |

---

## Database Initialization

The `db/init.sql` script runs on first startup and installs required extensions:

```sql
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- Trigram similarity
```

Tables are created automatically by SQLAlchemy ORM on startup via `init_db()`.

---

## Docker Images

### API Server (`backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]
```

### Temporal Worker (`backend/Dockerfile.worker`)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["python", "-m", "app.workflows.worker"]
```

---

## Production Considerations

{: .fedramp }
> **FedRAMP High** — Production deployments must meet FedRAMP High baseline requirements.

### Security Checklist

- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Enable `AUTH_REQUIRED=true` with Azure AD
- [ ] Configure TLS 1.3 via reverse proxy (nginx, Azure Front Door)
- [ ] Set `FIPS_MODE=true` for GovCloud
- [ ] Set `ENCRYPTION_AT_REST=true`
- [ ] Restrict CORS origins in `main.py`
- [ ] Enable audit log forwarding to SIEM

### Azure Deployment

For Azure Container Apps or Azure Kubernetes Service:

1. Push images to Azure Container Registry
2. Configure managed identity for PostgreSQL, Storage, and OpenAI
3. Use Azure Key Vault for secrets
4. Deploy with Azure Bicep templates (see `infra/` — upcoming)
5. Enable Azure Monitor for observability

### Scaling

| Component | Strategy |
|:----------|:---------|
| API | Horizontal scaling (stateless) |
| Worker | Scale with Temporal task queue depth |
| PostgreSQL | Azure Database for PostgreSQL Flexible Server |
| Embeddings | Azure OpenAI rate limiting / quota management |
