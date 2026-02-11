"""
Security Context — Identity & Access Control
==============================================
Ported from ctxEco's 4-layer enterprise context (Layer 1: Security).

Defines:
- Role: RBAC roles for users and agents
- SecurityContext: Identity object injected into every request

NIST AI RMF: GOVERN 1.2 (Accountability), MAP 1.5 (Boundaries)
"""

from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class Role(str, Enum):
    """User and agent roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    PM = "pm"
    VIEWER = "viewer"
    DEVELOPER = "developer"
    AGENT = "agent"  # AI agents / service accounts


class SecurityContext(BaseModel):
    """
    Layer 1: Identity and Access Control.

    Injected into every authenticated request via get_current_user().
    Used by ResourceAccessPolicy to enforce tenant, project, team,
    and user-level isolation across all resource types.
    """
    user_id: str
    tenant_id: str = "default"
    session_id: str = ""

    # Scoping
    project_id: Optional[str] = None
    team_id: Optional[str] = None

    # RBAC
    roles: list[Role] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)

    # OIDC 'groups' claim — used for team/department ACL matching
    # e.g., ["engineering", "security", "Dept:Finance"]
    groups: list[str] = Field(default_factory=list)

    # Identity metadata
    email: Optional[str] = None
    display_name: Optional[str] = None
    token_expiry: Optional[datetime] = None

    # Agent identity
    is_agent: bool = False
    agent_id: Optional[str] = None

    def has_role(self, role: Role) -> bool:
        """Check if user has a specific role. Admin implies all roles."""
        return role in self.roles or Role.ADMIN in self.roles

    def has_scope(self, scope: str) -> bool:
        """Check if user has a specific scope. Admin bypasses scope checks."""
        if Role.ADMIN in self.roles:
            return True
        return scope in self.scopes

    def get_resource_filter(self) -> dict:
        """Get filter dict for scoping resource queries."""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
        }
