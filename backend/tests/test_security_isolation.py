"""
Security Isolation Tests
=========================
Verifies multi-tenant and user-level isolation across resources.
Ported from ctxEco's test_memory_security_isolation.py.

Tests:
1. Tenant Isolation: Tenant A cannot see Tenant B resources.
2. User Isolation: User A cannot see User B's private resources.
3. Project Scoping: User with project_id=P cannot see project_id=Q resources.
4. Team Scoping: User with group=G can see team resources for group G.
5. Admin Override: Admin can see everything in their tenant.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import MagicMock

from app.core.security_context import SecurityContext, Role
from app.security.access_policy import ResourceAccessPolicy
from app.db.models import Document, ChunkRecord, GraphNodeRecord

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_document():
    return Document(
        id="doc-1",
        tenant_id="tenant-a",
        user_id="user-a",
        project_id="proj-x",
        access_level="team",
        acl_groups=["eng"],
    )

@pytest.fixture
def context_tenant_a_user_a():
    return SecurityContext(
        user_id="user-a",
        tenant_id="tenant-a",
        roles=[Role.VIEWER],
        groups=["eng"],
        project_id="proj-x",
    )

@pytest.fixture
def context_tenant_b_user_b():
    return SecurityContext(
        user_id="user-b",
        tenant_id="tenant-b",
        roles=[Role.VIEWER],
        groups=["marketing"],
    )

@pytest.fixture
def context_admin_tenant_a():
    return SecurityContext(
        user_id="admin-a",
        tenant_id="tenant-a",
        roles=[Role.ADMIN],
    )

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_tenant_isolation(mock_document, context_tenant_b_user_b):
    """Ensure cross-tenant access is strictly forbidden."""
    # User B (Tenant B) tries to access User A's doc (Tenant A)
    assert ResourceAccessPolicy.can_access(
        context_tenant_b_user_b,
        resource_tenant_id=mock_document.tenant_id,
        resource_user_id=mock_document.user_id,
        resource_access_level=mock_document.access_level,
    ) is False


def test_project_isolation():
    """Ensure project-level scoping works."""
    doc = Document(
        id="doc-2",
        tenant_id="tenant-a",
        user_id="user-b",
        project_id="proj-y",
        access_level="project",
    )
    
    # User in same tenant, but different project (proj-x)
    ctx = SecurityContext(
        user_id="user-a",
        tenant_id="tenant-a",
        project_id="proj-x",
    )
    
    assert ResourceAccessPolicy.can_access(
        ctx,
        resource_tenant_id=doc.tenant_id,
        resource_user_id=doc.user_id,
        resource_access_level=doc.access_level,
        resource_project_id=doc.project_id,
    ) is False
    
    # User in same tenant AND same project
    ctx_same_project = SecurityContext(
        user_id="user-c",
        tenant_id="tenant-a",
        project_id="proj-y",
    )
    
    assert ResourceAccessPolicy.can_access(
        ctx_same_project,
        resource_tenant_id=doc.tenant_id,
        resource_user_id=doc.user_id,
        resource_access_level=doc.access_level,
        resource_project_id=doc.project_id,
    ) is True


def test_team_access(mock_document):
    """Ensure team (ACL group) access works."""
    # User in 'eng' group should access 'team' level doc with 'eng' in acl
    ctx_eng = SecurityContext(
        user_id="user-c",
        tenant_id="tenant-a",
        groups=["eng", "other"],
    )
    assert ResourceAccessPolicy.can_access(
        ctx_eng,
        resource_tenant_id=mock_document.tenant_id,
        resource_user_id=mock_document.user_id,
        resource_access_level="team",
        resource_acl_groups=["eng"],
    ) is True

    # User NOT in 'eng' group should FAIL
    ctx_marketing = SecurityContext(
        user_id="user-d",
        tenant_id="tenant-a",
        groups=["marketing"],
    )
    assert ResourceAccessPolicy.can_access(
        ctx_marketing,
        resource_tenant_id=mock_document.tenant_id,
        resource_user_id=mock_document.user_id,
        resource_access_level="team",
        resource_acl_groups=["eng"],
    ) is False


def test_private_access():
    """Ensure 'private' access level restricts to owner only."""
    doc = Document(
        id="doc-private",
        tenant_id="tenant-a",
        user_id="user-a",
        access_level="private",
    )
    
    # Owner access
    ctx_owner = SecurityContext(user_id="user-a", tenant_id="tenant-a")
    assert ResourceAccessPolicy.can_access(
        ctx_owner,
        resource_tenant_id=doc.tenant_id,
        resource_user_id=doc.user_id,
        resource_access_level=doc.access_level,
    ) is True
    
    # Other user in same tenant
    ctx_other = SecurityContext(user_id="user-b", tenant_id="tenant-a")
    assert ResourceAccessPolicy.can_access(
        ctx_other,
        resource_tenant_id=doc.tenant_id,
        resource_user_id=doc.user_id,
        resource_access_level=doc.access_level,
    ) is False


def test_admin_override(mock_document, context_admin_tenant_a):
    """Ensure admins can access everything within their tenant."""
    # Admin is not owner, not in group, not in project
    # But has Role.ADMIN
    assert ResourceAccessPolicy.can_access(
        context_admin_tenant_a,
        resource_tenant_id=mock_document.tenant_id,
        resource_user_id=mock_document.user_id,
        resource_access_level="private",  # Even private docs? access_policy.py says YES for now
    ) is True


def test_system_resource_access():
    """Ensure system resources are accessible to specific roles."""
    ctx_analyst = SecurityContext(
        user_id="user-analyst",
        tenant_id="tenant-a",
        roles=[Role.ANALYST],
    )
    ctx_viewer = SecurityContext(
        user_id="user-viewer",
        tenant_id="tenant-a",
        roles=[Role.VIEWER],
    )
    
    # System resource
    assert ResourceAccessPolicy.can_access(
        ctx_analyst,
        resource_tenant_id="tenant-a",
        resource_user_id="system",
    ) is True
    
    # Viewer cannot see system resources (unless default policy changes)
    # access_policy.py: SYSTEM_RESOURCE_ROLES = [ADMIN, ANALYST, PM]
    assert ResourceAccessPolicy.can_access(
        ctx_viewer,
        resource_tenant_id="tenant-a",
        resource_user_id="system",
    ) is False
