"""
Resource Access Policy — Unified Authorization
================================================
Adapted from ctxEco's MemoryAccessPolicy.

Provides tenant, project, team, and user-level isolation
across ALL resource types: documents, chunks, graph nodes,
graph edges, and connectors.

NIST AI RMF: MANAGE 2.3 — Departmental/Project Isolation
"""

from typing import Any, Optional

from sqlalchemy import and_, or_

from app.core.security_context import SecurityContext, Role


class ResourceAccessPolicy:
    """
    Unified access control for all resources.

    Enforcement hierarchy:
    1. Tenant isolation (MANDATORY — never bypassed)
    2. Admin override (within tenant only)
    3. Owner access (user_id match)
    4. Access level: private → team → project → tenant

    Access Levels:
    - "private"  : Only the owner (user_id)
    - "team"     : Members sharing an acl_groups entry
    - "project"  : Anyone with the same project_id
    - "tenant"   : All authenticated users in the organization
    """

    # Roles that can access system-ingested resources (user_id="system")
    SYSTEM_RESOURCE_ROLES = [Role.ADMIN, Role.ANALYST, Role.PM]

    # Roles that can access any user's resources within their tenant
    TENANT_ADMIN_ROLES = [Role.ADMIN]

    @classmethod
    def can_access(
        cls,
        ctx: SecurityContext,
        resource_tenant_id: str,
        resource_user_id: str,
        resource_access_level: str = "team",
        resource_project_id: Optional[str] = None,
        resource_acl_groups: Optional[list[str]] = None,
    ) -> bool:
        """
        Check if the user can access a specific resource.

        Works for any resource type — documents, chunks, graph nodes, etc.

        Args:
            ctx: The authenticated user's SecurityContext
            resource_tenant_id: Tenant that owns the resource
            resource_user_id: User that created the resource
            resource_access_level: "private" | "team" | "project" | "tenant"
            resource_project_id: Project the resource belongs to
            resource_acl_groups: ACL groups on the resource
        """
        # SECURITY: Tenant isolation is ALWAYS mandatory
        if ctx.tenant_id != resource_tenant_id:
            return False

        # Admin override within tenant
        if Role.ADMIN in ctx.roles:
            return True

        # Owner always has access to their own resources
        if ctx.user_id == resource_user_id:
            return True

        # System resources (user_id="system") follow role-based access
        if resource_user_id == "system":
            return cls.can_access_system_resources(ctx)

        # Check access_level hierarchy
        if resource_access_level == "private":
            return False  # Only owner (checked above)

        if resource_access_level == "team":
            if resource_acl_groups:
                return bool(set(ctx.groups) & set(resource_acl_groups))
            return False

        if resource_access_level == "project":
            return (
                ctx.project_id is not None
                and resource_project_id is not None
                and ctx.project_id == resource_project_id
            )

        if resource_access_level == "tenant":
            return True  # Same tenant already verified above

        return False

    @classmethod
    def can_access_system_resources(cls, ctx: SecurityContext) -> bool:
        """
        Check if user can access system-ingested resources.

        System resources (user_id="system") are typically documentation
        or organizational knowledge ingested programmatically.
        """
        return any(role in cls.SYSTEM_RESOURCE_ROLES for role in ctx.roles)

    @classmethod
    def build_query_filter(cls, ctx: SecurityContext, query: Any, model: Any) -> Any:
        """
        Apply mandatory access filters at the SQL level.

        Works on ANY model with tenant_id. Also applies access_level
        filtering if the model has access_level, user_id, project_id,
        and acl_groups columns.

        This ensures filtering happens BEFORE pagination — no data leaks.

        Args:
            ctx: The authenticated user's SecurityContext
            query: SQLAlchemy select() query
            model: The ORM model class (Document, ChunkRecord, etc.)

        Returns:
            Filtered query
        """
        # MANDATORY: Tenant isolation
        query = query.where(model.tenant_id == ctx.tenant_id)

        # Admin sees everything within their tenant
        if Role.ADMIN in ctx.roles:
            return query

        # Non-admin: apply access level rules
        if hasattr(model, "access_level") and hasattr(model, "user_id"):
            conditions = [
                # Always see own resources
                model.user_id == ctx.user_id,
                # Tenant-wide resources
                model.access_level == "tenant",
                # System resources for authorized roles
            ]

            if cls.can_access_system_resources(ctx):
                conditions.append(model.user_id == "system")

            # Project scoping
            if ctx.project_id and hasattr(model, "project_id"):
                conditions.append(
                    and_(
                        model.access_level == "project",
                        model.project_id == ctx.project_id,
                    )
                )

            # Team/group scoping
            if ctx.groups and hasattr(model, "acl_groups"):
                conditions.append(
                    and_(
                        model.access_level == "team",
                        model.acl_groups.overlap(ctx.groups),
                    )
                )

            query = query.where(or_(*conditions))

        return query

    @classmethod
    def filter_accessible_resources(
        cls,
        ctx: SecurityContext,
        resources: list[dict],
    ) -> list[dict]:
        """
        Post-query filter for resources returned as dicts.

        Use build_query_filter() for SQL-level filtering when possible.
        This is a fallback for non-SQL scenarios (e.g., graph traversals).
        """
        accessible = []
        for resource in resources:
            resource_user_id = resource.get("user_id", "")
            resource_tenant_id = resource.get("tenant_id", "")
            resource_access_level = resource.get("access_level", "team")
            resource_project_id = resource.get("project_id")
            resource_acl_groups = resource.get("acl_groups", [])

            if not resource_tenant_id:
                # Legacy resource without tenant — allow if owner or system
                if resource_user_id == ctx.user_id or resource_user_id == "system":
                    accessible.append(resource)
                continue

            if cls.can_access(
                ctx,
                resource_tenant_id=resource_tenant_id,
                resource_user_id=resource_user_id,
                resource_access_level=resource_access_level,
                resource_project_id=resource_project_id,
                resource_acl_groups=resource_acl_groups,
            ):
                accessible.append(resource)

        return accessible
