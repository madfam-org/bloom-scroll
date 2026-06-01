"""
Janua Authentication Integration for Bloom Scroll

Provides JWT verification and user extraction for API endpoints.
Tokens are issued by Janua (MADFAM's centralized auth service).
"""

import time
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from app.core.config import settings

# Security scheme for JWT Bearer tokens
security = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expires_at = 0.0


class User(BaseModel):
    """Authenticated user from Janua JWT."""

    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    roles: list[str] = []
    permissions: list[str] = []
    org_id: str | None = None


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # User ID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    roles: list[str] = []
    permissions: list[str] = []
    org_id: str | None = None
    exp: int
    iat: int
    iss: str = "janua"


def _configured_algorithm() -> str:
    """Return the configured JWT algorithm in canonical uppercase form."""
    return settings.JANUA_JWT_ALGORITHM.strip().upper()


def _decode_options() -> dict[str, bool]:
    """Build python-jose verification options from settings."""
    return {
        "verify_exp": True,
        "verify_aud": bool(settings.JANUA_JWT_AUDIENCE),
        "verify_iss": bool(settings.JANUA_JWT_ISSUER),
    }


def _get_jwks() -> dict[str, Any]:
    """Fetch and cache Janua JWKS keys for RS256 verification."""
    global _jwks_cache, _jwks_cache_expires_at

    now = time.time()
    if _jwks_cache is not None and now < _jwks_cache_expires_at:
        return _jwks_cache

    response = httpx.get(settings.JANUA_JWKS_URI, timeout=5)
    response.raise_for_status()
    jwks = response.json()
    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise ValueError("Invalid JWKS response")

    _jwks_cache = jwks
    _jwks_cache_expires_at = now + settings.JANUA_JWKS_CACHE_SECONDS
    return jwks


def _select_jwk(token: str) -> dict[str, Any] | None:
    """Select the JWKS key matching the token's kid header."""
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg")
    if alg != _configured_algorithm():
        return None

    keys = _get_jwks().get("keys", [])
    for key in keys:
        if not isinstance(key, dict):
            continue
        if kid and key.get("kid") == kid:
            return key

    if not kid and len(keys) == 1 and isinstance(keys[0], dict):
        return keys[0]

    return None


def _decode_jwt(token: str) -> dict[str, Any]:
    """Decode a Janua JWT using RS256 JWKS or explicit HS256 fallback."""
    algorithm = _configured_algorithm()
    audience = settings.JANUA_JWT_AUDIENCE or None
    issuer = settings.JANUA_JWT_ISSUER or None

    if algorithm == "RS256":
        jwk = _select_jwk(token)
        if not jwk:
            raise JWTError("No matching JWKS key")
        return cast(dict[str, Any], jwt.decode(
            token,
            jwk,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options=_decode_options(),
        ))

    if algorithm.startswith("HS"):
        return cast(dict[str, Any], jwt.decode(
            token,
            settings.JANUA_JWT_SECRET,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
            options=_decode_options(),
        ))

    raise JWTError(f"Unsupported Janua JWT algorithm: {algorithm}")


def _payload_from_claims(payload: dict[str, Any]) -> TokenPayload:
    """Normalize decoded claims into the API's user payload model."""
    sub = payload.get("sub")
    email = payload.get("email")
    exp = payload.get("exp")
    iat = payload.get("iat")
    if not isinstance(sub, str) or not sub:
        raise ValueError("JWT missing sub")
    if not isinstance(email, str) or not email:
        raise ValueError("JWT missing email")
    if not isinstance(exp, int):
        raise ValueError("JWT missing exp")
    if not isinstance(iat, int):
        raise ValueError("JWT missing iat")

    roles = payload.get("roles", [])
    permissions = payload.get("permissions", [])

    return TokenPayload(
        sub=sub,
        email=email,
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
        roles=roles if isinstance(roles, list) else [],
        permissions=permissions if isinstance(permissions, list) else [],
        org_id=payload.get("org_id"),
        exp=exp,
        iat=iat,
        iss=payload.get("iss", "janua"),
    )


def verify_token(token: str) -> TokenPayload | None:
    """
    Verify a Janua JWT token.

    Args:
        token: JWT access token from Janua

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        return _payload_from_claims(_decode_jwt(token))
    except (JWTError, ValueError, ValidationError, httpx.HTTPError):
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    """
    FastAPI dependency to get current authenticated user.

    Raises HTTPException 401 if not authenticated.
    """
    if not settings.AUTH_ENABLED:
        # Return a mock user for development when auth is disabled
        return User(
            id="dev-user",
            email="dev@madfam.io",
            first_name="Dev",
            last_name="User",
            roles=["user"],
            permissions=["read", "write"],
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_payload = verify_token(credentials.credentials)

    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(
        id=token_payload.sub,
        email=token_payload.email,
        first_name=token_payload.first_name,
        last_name=token_payload.last_name,
        roles=token_payload.roles,
        permissions=token_payload.permissions,
        org_id=token_payload.org_id,
    )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    """
    FastAPI dependency to get current user if authenticated.

    Returns None if not authenticated (doesn't raise exception).
    """
    if not credentials:
        return None

    token_payload = verify_token(credentials.credentials)

    if not token_payload:
        return None

    return User(
        id=token_payload.sub,
        email=token_payload.email,
        first_name=token_payload.first_name,
        last_name=token_payload.last_name,
        roles=token_payload.roles,
        permissions=token_payload.permissions,
        org_id=token_payload.org_id,
    )


def require_role(required_role: str) -> Callable[..., Awaitable[User]]:
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user

    return role_checker


def require_permission(required_permission: str) -> Callable[..., Awaitable[User]]:
    """
    Dependency factory for permission-based access control.

    Usage:
        @router.delete("/items/{id}")
        async def delete_item(user: User = Depends(require_permission("delete"))):
            ...
    """

    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        if required_permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )
        return user

    return permission_checker
