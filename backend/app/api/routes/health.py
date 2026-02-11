"""Health check endpoint."""

from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/ready")
async def ready():
    """Readiness probe — checks database connectivity."""
    try:
        from app.db.session import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "ready": db_ok,
        "database": "connected" if db_ok else "unavailable",
    }
