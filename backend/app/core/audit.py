"""
Audit Logging — NIST AI RMF / FedRAMP Compliance
==================================================
Ported from ctxEco's audit logger.

Provides comprehensive audit trail for:
- Security events (login, access denied)
- Resource events (ingest, search, access, delete)
- Agent actions (tool calls, responses)
- Administrative actions (config changes)

NIST AI RMF: MANAGE 4.2 (Audit), GOVERN 1.2 (Accountability)
"""

import logging
import json
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps

logger = logging.getLogger("audit")


class AuditEventType(str, Enum):
    """Categories of auditable events."""
    # Security events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"
    ACCESS_DENIED = "auth.access_denied"
    TOKEN_EXPIRED = "auth.token_expired"

    # Resource events (documents, chunks, graph, connectors)
    RESOURCE_INGEST = "resource.ingest"
    RESOURCE_SEARCH = "resource.search"
    RESOURCE_ACCESS = "resource.access"
    RESOURCE_UPDATE = "resource.update"
    RESOURCE_DELETE = "resource.delete"

    # Graph events
    GRAPH_QUERY = "graph.query"
    GRAPH_BUILD = "graph.build"

    # Agent events
    AGENT_ACTION = "agent.action"
    AGENT_TOOL_CALL = "agent.tool_call"
    AGENT_ERROR = "agent.error"

    # Connector events
    CONNECTOR_SYNC = "connector.sync"
    CONNECTOR_ERROR = "connector.error"

    # Admin events
    ADMIN_CONFIG_CHANGE = "admin.config_change"
    ADMIN_ROLE_CHANGE = "admin.role_change"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"


@dataclass
class AuditEvent:
    """
    Structured audit event record.
    All fields designed for SIEM integration and compliance reporting.
    """
    event_type: AuditEventType
    timestamp: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    project_id: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    agent_id: Optional[str]
    action: str
    resource: Optional[str]
    resource_type: Optional[str]
    outcome: str  # "success", "failure", "denied"
    details: dict
    ip_address: Optional[str]
    user_agent: Optional[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string for structured logging."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Audit logging service with structured JSON output.

    Outputs:
    - Python logging (structured JSON)
    - Extensible to Azure Monitor / OpenTelemetry
    """

    def __init__(self, app_name: str = "doc-ingestion-router"):
        self.app_name = app_name
        self._setup_logger()

    def _setup_logger(self):
        """Configure the audit logger."""
        self._logger = logging.getLogger("audit")
        self._logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        if not self._logger.handlers:
            self._logger.addHandler(handler)

    def log(
        self,
        event_type: AuditEventType,
        action: str,
        outcome: str = "success",
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log an audit event."""
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            session_id=session_id,
            request_id=request_id,
            agent_id=agent_id,
            action=action,
            resource=resource,
            resource_type=resource_type,
            outcome=outcome,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        log_level = logging.WARNING if outcome in ("failure", "denied") else logging.INFO
        self._logger.log(log_level, event.to_json())

    def log_security_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        outcome: str,
        details: dict = None,
        ip_address: str = None,
    ):
        """Convenience method for security events."""
        self.log(
            event_type=event_type,
            action=event_type.value.split(".")[-1],
            outcome=outcome,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )

    def log_resource_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        tenant_id: str,
        resource_type: str,
        resource_id: str = None,
        project_id: str = None,
        details: dict = None,
    ):
        """Convenience method for resource operations."""
        self.log(
            event_type=event_type,
            action=event_type.value.split(".")[-1],
            outcome="success",
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            resource=resource_id,
            resource_type=resource_type,
            details=details,
        )

    def log_agent_action(
        self,
        agent_id: str,
        action: str,
        user_id: str,
        details: dict = None,
        outcome: str = "success",
    ):
        """Convenience method for agent actions."""
        self.log(
            event_type=AuditEventType.AGENT_ACTION,
            action=action,
            outcome=outcome,
            user_id=user_id,
            agent_id=agent_id,
            details=details,
        )


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions
def audit_log(event_type: AuditEventType, action: str, **kwargs):
    """Quick audit log function."""
    get_audit_logger().log(event_type, action, **kwargs)


def audit_security(event_type: AuditEventType, user_id: str, outcome: str, **kwargs):
    """Quick security audit log."""
    get_audit_logger().log_security_event(event_type, user_id, outcome, **kwargs)


# Decorator for auditing function calls
def audited(event_type: AuditEventType, action: str = None):
    """
    Decorator to automatically audit function calls.

    Usage:
        @audited(AuditEventType.RESOURCE_SEARCH, action="trisearch")
        async def search(query: str, user_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            try:
                result = await func(*args, **kwargs)
                audit_log(
                    event_type,
                    action or func.__name__,
                    user_id=str(user_id) if user_id else None,
                    outcome="success",
                )
                return result
            except Exception as e:
                audit_log(
                    event_type,
                    action or func.__name__,
                    user_id=str(user_id) if user_id else None,
                    outcome="failure",
                    details={"error": str(e)},
                )
                raise
        return wrapper
    return decorator
