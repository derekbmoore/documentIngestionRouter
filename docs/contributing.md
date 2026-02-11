---
layout: default
title: Contributing
nav_order: 11
---

# Contributing

{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Welcome

The Document Ingestion Router is **MIT-licensed** open-source software maintained by [Zimax Networks LC](https://zimax.net). Contributions are welcome! This guide covers the dev setup, coding standards, and PR process.

---

## Development Setup

### Prerequisites

| Tool | Version |
|:-----|:--------|
| Python | 3.11+ |
| Docker & Docker Compose | 24+ |
| Git | 2.x |

### Local Setup

```bash
# Clone
git clone https://github.com/derekbmoore/documentIngestionRouter.git
cd documentIngestionRouter

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Install spaCy model
python -m spacy download en_core_web_sm

# Start infrastructure (Postgres, Temporal, Zep)
docker compose up postgres temporal temporal-ui zep -d

# Configure
cp .env.example .env
# Edit .env: set POSTGRES_HOST=localhost

# Run API server
cd backend
uvicorn app.main:app --reload --port 8082
```

---

## Project Structure

```
backend/app/
├── main.py              # FastAPI entry point
├── config.py            # Pydantic settings
├── router/              # Classification engine
│   ├── classifier.py    # Document Ingestion Router
│   └── models.py        # Pydantic models
├── engines/             # Extraction engines
│   ├── base.py          # Abstract interface
│   ├── docling_engine.py
│   ├── unstructured_engine.py
│   └── pandas_engine.py
├── search/              # TriSearch™
│   └── trisearch.py
├── graph/               # Knowledge graph
│   └── knowledge.py
├── connectors/          # 16 data source connectors
│   └── registry.py
├── workflows/           # Temporal workflows
│   ├── ingestion.py
│   └── worker.py
├── db/                  # Database models
│   ├── models.py
│   └── session.py
└── api/                 # HTTP routes + middleware
    ├── routes/
    └── middleware/
```

---

## Coding Standards

### Python

- **Style**: PEP 8, enforced with `ruff` or `black`
- **Type hints**: Required on all public functions
- **Docstrings**: Required on all classes and public methods
- **Models**: Use Pydantic for all data models
- **Logging**: Use `structlog`, not `print()` or stdlib `logging`
- **Async**: All database and I/O operations must be `async`

### Documentation

- **Format**: Just the Docs (Jekyll) with GitHub Flavored Markdown
- **Front matter**: Required `layout`, `title`, `nav_order` on every page
- **Diagrams**: Mermaid for architecture and flow diagrams

### Compliance

When adding new features, include NIST AI RMF control references in docstrings:

```python
"""
Process a document.

NIST AI RMF: MAP 1.5 — Provenance preserved in metadata.
"""
```

---

## Pull Request Process

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/my-feature`
3. **Make changes** following the coding standards above
4. **Test** your changes locally
5. **Commit** with a clear message: `git commit -m "Add: new connector for X"`
6. **Push** to your fork: `git push origin feature/my-feature`
7. **Open a PR** against `main`

### Commit Message Format

```
<type>: <description>

Types: Add, Fix, Update, Remove, Refactor, Docs
```

### PR Review Criteria

- [ ] Follows coding standards
- [ ] Includes docstrings and type hints
- [ ] No secrets or credentials in code
- [ ] NIST/FedRAMP controls referenced where applicable
- [ ] Documentation updated if user-facing behavior changes

---

## Adding a New Connector

1. Create a new class in `backend/app/connectors/registry.py`
2. Extend `BaseConnector` and implement `connect()`, `list_documents()`, `fetch_document()`
3. Add the class to `CONNECTOR_REGISTRY`
4. Add the kind to `ConnectorKind` enum in `router/models.py`
5. Document the connector in `docs/connectors.md`

```python
class MyConnector(BaseConnector):
    kind = "MyService"
    category = "collaboration"
    icon = "🆕"
    description = "Sync from MyService"

    async def connect(self) -> bool: ...
    async def list_documents(self) -> List[Dict[str, Any]]: ...
    async def fetch_document(self, doc_id: str, dest_path: str) -> str: ...
```

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](https://github.com/derekbmoore/documentIngestionRouter/blob/main/LICENSE).
