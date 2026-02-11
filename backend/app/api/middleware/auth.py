"""
OIDC Authentication Middleware
===============================
Ported from ctxEco's auth middleware.

Provides JWT-based authentication for:
- Azure AD / Entra ID
- Any OIDC-compliant provider

NIST AI RMF: GOVERN 1.2 (Accountability), MAP 1.5 (Boundaries)
"""

import logging
import os
from typing import Optional
from datetime import datetime, timezone

import httpx
from jose import jwt, JWTError
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security_context import SecurityContext, Role

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Decoded JWT token payload from OIDC provider."""
    sub: str                      # Subject (user identifier)
    oid: Optional[str] = None     # Object ID (Azure AD specific)
    tid: Optional[str] = None     # Tenant ID
    preferred_username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = []
    scp: Optional[str] = None     # Scopes
    aud: str = ""                 # Audience
    iss: str = ""                 # Issuer
    exp: int = 0                  # Expiration
    iat: int = 0                  # Issued at
    groups: list[str] = []        # Security Groups (Group IDs)
    wids: list[str] = []          # Directory Roles (Well-known IDs)


class OIDCAuth:
    """
    OIDC Authentication Handler.

    Validates JWT tokens from any OIDC-compliant provider.
    Supports Azure AD, Entra External ID, Keycloak, etc.
    """

    def __init__(self):
        """Initialize from environment variables."""
        self._issuer_url = os.getenv("OIDC_ISSUER_URL", "")
        self._client_id = os.getenv("OIDC_CLIENT_ID", "")
        self._audience = os.getenv("OIDC_AUDIENCE", self._client_id)

        # Azure AD auto-configuration
        if not self._issuer_url:
            tenant_id = os.getenv("AZURE_AD_TENANT_ID")
            external_domain = os.getenv("AZURE_AD_EXTERNAL_DOMAIN")
            is_external = os.getenv("AZURE_AD_EXTERNAL_ID", "false").lower() == "true"

            if tenant_id:
                if is_external and external_domain:
                    self._issuer_url = f"https://{external_domain}.ciamlogin.com/{tenant_id}/v2.0"
                else:
                    self._issuer_url = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

                logger.info(f"Autoconfigured OIDC Issuer: {self._issuer_url}")

        if not self._client_id:
            self._client_id = os.getenv("AZURE_AD_CLIENT_ID", "")
            if not self._audience:
                self._audience = self._client_id

        self._jwks: Optional[dict] = None
        self._jwks_uri: Optional[str] = None

    async def get_jwks(self) -> dict:
        """Fetch and cache JWKS (JSON Web Key Set) for signature verification."""
        if self._jwks is not None:
            return self._jwks

        if not self._issuer_url:
            raise ValueError("OIDC_ISSUER_URL not configured")

        async with httpx.AsyncClient() as client:
            discovery_url = f"{self._issuer_url.rstrip('/')}/.well-known/openid-configuration"
            response = await client.get(discovery_url)
            response.raise_for_status()
            config = response.json()
            self._jwks_uri = config.get("jwks_uri")

            if not self._jwks_uri:
                raise ValueError("JWKS URI not found in OIDC configuration")

            jwks_response = await client.get(self._jwks_uri)
            jwks_response.raise_for_status()
            self._jwks = jwks_response.json()

        return self._jwks

    async def validate_token(self, token: str) -> TokenPayload:
        """
        Validate a JWT token from the OIDC provider.

        Returns:
            TokenPayload with decoded claims

        Raises:
            HTTPException if validation fails
        """
        try:
            jwks = await self.get_jwks()

            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer_url,
                options={"verify_exp": True},
            )

            return TokenPayload(**payload)

        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def map_roles(self, token_roles: list[str]) -> list[Role]:
        """
        Map OIDC roles to application roles.

        Supports direct and prefixed role names:
        - "admin" → Role.ADMIN
        - "App.Admin" → Role.ADMIN
        - "Engram.Analyst" → Role.ANALYST
        """
        role_mapping = {
            "admin": Role.ADMIN,
            "analyst": Role.ANALYST,
            "pm": Role.PM,
            "viewer": Role.VIEWER,
            "developer": Role.DEVELOPER,
            "agent": Role.AGENT,
        }

        mapped = []
        for role in token_roles:
            role_name = role.split(".")[-1].lower()
            if role_name in role_mapping:
                mapped.append(role_mapping[role_name])

        return mapped

    def extract_scopes(self, token: TokenPayload) -> list[str]:
        """Extract scopes from token."""
        if token.scp:
            return token.scp.split(" ")
        return []


# Global auth instance
_auth: Optional[OIDCAuth] = None


def get_auth() -> OIDCAuth:
    """Get or create the auth instance."""
    global _auth
    if _auth is None:
        _auth = OIDCAuth()
    return _auth


def _get_auth_required() -> bool:
    """Check if authentication is required."""
    return os.getenv("AUTH_REQUIRED", "true").lower() == "true"


def _get_poc_user_context() -> SecurityContext:
    """Build a default SecurityContext when auth is disabled (dev mode)."""
    return SecurityContext(
        user_id=os.getenv("POC_USER_ID", "poc-user"),
        tenant_id=os.getenv("POC_TENANT_ID", "default"),
        roles=[Role.ADMIN],
        scopes=["*"],
        email=os.getenv("POC_USER_EMAIL", "poc@example.com"),
        display_name=os.getenv("POC_USER_NAME", "POC User"),
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> SecurityContext:
    """
    FastAPI dependency — returns the authenticated user's SecurityContext.

    In production (AUTH_REQUIRED=true):
        Validates JWT, extracts tenant_id, roles, groups.

    In development (AUTH_REQUIRED=false):
        Returns a POC user with admin privileges.

    Usage:
        @router.get("/protected")
        async def protected(ctx: SecurityContext = Depends(get_current_user)):
            return {"user": ctx.user_id, "tenant": ctx.tenant_id}
    """
    if not _get_auth_required():
        logger.debug("Auth disabled, returning POC user")
        return _get_poc_user_context()

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth = get_auth()
    token = await auth.validate_token(credentials.credentials)

    ctx = SecurityContext(
        user_id=token.oid or token.sub,
        tenant_id=token.tid or "default",
        roles=auth.map_roles(token.roles),
        scopes=auth.extract_scopes(token),
        email=token.email or token.preferred_username,
        display_name=token.name,
        token_expiry=(
            datetime.fromtimestamp(token.exp, tz=timezone.utc)
            if token.exp else None
        ),
        groups=token.groups + token.wids,
    )
    
    # Attach to request access by AuditMiddleware
    request.state.user = ctx
    return ctx


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[SecurityContext]:
    """
    Get current user if authenticated, otherwise return None.
    Used for endpoints with mixed auth requirements.
    """
    if not credentials:
        return None

    try:
        auth = get_auth()
        token = await auth.validate_token(credentials.credentials)

        return SecurityContext(
            user_id=token.oid or token.sub,
            tenant_id=token.tid or "default",
            roles=auth.map_roles(token.roles),
            scopes=auth.extract_scopes(token),
            email=token.email or token.preferred_username,
            display_name=token.name,
            token_expiry=(
                datetime.fromtimestamp(token.exp, tz=timezone.utc)
                if token.exp else None
            ),
            groups=token.groups + token.wids,
        )
    except Exception:
        return None


def require_roles(*required_roles: Role):
    """
    Dependency factory to require specific roles.

    Usage:
        @router.get("/admin")
        async def admin_route(
            ctx: SecurityContext = Depends(require_roles(Role.ADMIN))
        ):
            return {"admin": True}
    """
    async def role_checker(
        user: SecurityContext = Depends(get_current_user),
    ) -> SecurityContext:
        for role in required_roles:
            if user.has_role(role):
                return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required roles: {[r.value for r in required_roles]}",
        )

    return role_checker


def require_scopes(*required_scopes: str):
    """
    Dependency factory to require specific scopes.

    Usage:
        @router.get("/data")
        async def data_route(
            ctx: SecurityContext = Depends(require_scopes("data:read"))
        ):
            ...
    """
    async def scope_checker(
        user: SecurityContext = Depends(get_current_user),
    ) -> SecurityContext:
        for scope in required_scopes:
            if not user.has_scope(scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required scope: {scope}",
                )
        return user

    return scope_checker
