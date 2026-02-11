"""
Audit Middleware
=================
Intercepts HTTP requests and logs them via the structured AuditLogger.

Collects:
- Request method, path, query params
- Response status code, duration
- User identity (from request.state.user)
- Request ID, Session ID

NIST AI RMF: MANAGE 4.2 (Audit)
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.audit import get_audit_logger, AuditEventType


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging of all HTTP traffic.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_audit_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Attach request_id to request state for downstream use
        request.state.request_id = request_id

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract user context if available (set by AuthMiddleware)
            user_context = getattr(request.state, "user", None)
            user_id = user_context.user_id if user_context else None
            tenant_id = user_context.tenant_id if user_context else None
            project_id = user_context.project_id if user_context else None
            session_id = user_context.session_id if user_context else None

            # Determine outcomes
            outcome = "success"
            if response.status_code >= 400:
                outcome = "failure"
            if response.status_code in (401, 403):
                outcome = "denied"

            # Log event
            self.logger.log(
                event_type=AuditEventType.RESOURCE_ACCESS,
                action="http_request",
                outcome=outcome,
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                session_id=session_id,
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log(
                event_type=AuditEventType.SYSTEM_ERROR,
                action="http_request_error",
                outcome="failure",
                request_id=request_id,
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise
