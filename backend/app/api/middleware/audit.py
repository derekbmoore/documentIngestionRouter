"""
Audit Middleware — FedRAMP / NIST AI RMF Compliance
=====================================================
Logs all API requests for audit trail.

NIST AI RMF: GOVERN 1.1 — All actions are logged.
FedRAMP High: AU-2 — Audit events are captured.
"""

import uuid
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        start = time.time()

        # Log request
        logger.info(
            "api.request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        response: Response = await call_next(request)

        # Log response
        duration_ms = round((time.time() - start) * 1000, 2)
        logger.info(
            "api.response",
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
