"""
Document Ingestion Router — FastAPI + MCP Server
=================================================
Main entry point for the Document Ingestion Router MCP server.

Part of the Context Ecology (ctxEco) platform.
Product of Zimax Networks LC — MIT License (open-source).

NIST AI RMF: GOVERN 1.1 — Explicit policies and entry point governance.
"""

import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import ingest, search, connectors, graph, health
from app.api.middleware.audit import AuditMiddleware
from app.db.session import init_db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    ),
)
logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info(
        "Starting Document Ingestion Router",
        version=settings.app_version,
        fips_mode=settings.fips_mode,
    )
    await init_db()
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield
    logger.info("Shutting down Document Ingestion Router")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "MCP Server for intelligent document ingestion, classification, "
        "and TriSearch™ indexing. Part of the Context Ecology (ctxEco) platform. "
        "Commercially supported by Zimax Networks LC."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8082"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit logging
app.add_middleware(AuditMiddleware)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

app.include_router(health.router, tags=["Health"])
app.include_router(ingest.router, prefix=API_PREFIX, tags=["Ingestion"])
app.include_router(search.router, prefix=API_PREFIX, tags=["Search"])
app.include_router(connectors.router, prefix=API_PREFIX, tags=["Connectors"])
app.include_router(graph.router, prefix=API_PREFIX, tags=["Graph Knowledge"])


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "product": "Zimax Networks LC",
        "license": "MIT",
        "docs": "/docs",
    }
