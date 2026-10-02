"""
Janua Authentication Integration for Bloom Scroll

Provides JWT verification and user extraction for API endpoints.
Tokens are issued by Janua (MADFAM's centralized auth service).
"""

import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from jwt.types import Options
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Security scheme for JWT Bearer tokens
security = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expires_at = 0.0

# Janua rotates its signing key with a hard cut (no overlap window), so a token
# whose `kid` is not in the cached JWKS triggers one forced re-fetch before it
# is rejected. Forced re-fetches are rate-limited per process, so tokens with
# forged `kid` values cannot turn into a stream of requests to Janua.
JWKS_FORCED_REFRESH_MIN_INTERVAL_SECONDS = 60.0
_jwks_forced_refresh_at: float | None = None

# The only algorithm a Janua RS256 token may use. Fixed here, never taken from
# the token header or the JWK.
_RS256 = "RS256"

_audience_unset_warned = False

# Clock skew tolerated on exp / nbf / iat, in seconds. PyJWT rejects an `iat`
# in the future (python-jose did not), and a Janua token is verified moments
# after it is minted, so with zero leeway any lag of this host's clock behind
# Janua's would reject valid sessions.
JWT_LEEWAY_SECONDS = 30


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


def _expected_audience() -> str | None:
    """Return the audience every token must carry, or None when not enforced.

    Fail closed: when ``JANUA_JWT_AUDIENCE`` is empty and
    ``JANUA_JWT_AUDIENCE_REQUIRED`` is true (the default), no Janua token is
    accepted, because without an audience any token Janua issues to any client
    would verify here. ``JANUA_JWT_AUDIENCE_REQUIRED=false`` restores the
    unchecked behaviour explicitly (local development only).

    Raises:
        jwt.InvalidAudienceError: audience required but not configured.
    """
    global _audience_unset_warned

    audience = settings.JANUA_JWT_AUDIENCE.strip()
    if audience:
        return audience
    if settings.JANUA_JWT_AUDIENCE_REQUIRED:
        if not _audience_unset_warned:
            logger.warning(
                "JANUA_JWT_AUDIENCE is not set and JANUA_JWT_AUDIENCE_REQUIRED is true: "
                "rejecting every Janua bearer token (fail closed)"
            )
            _audience_unset_warned = True
        raise jwt.InvalidAudienceError("JANUA_JWT_AUDIENCE is required but not configured")
    return None


def _decode_options(audience: str | None) -> Options:
    """Build PyJWT verification options from settings."""
    return {
        "verify_exp": True,
        "verify_aud": audience is not None,
        "verify_iss": bool(settings.JANUA_JWT_ISSUER),
        "require": ["exp"],
    }


def _claim_forced_refresh() -> bool:
    """Return True when a forced JWKS re-fetch is allowed now, and record it.

    At most one forced re-fetch per ``JWKS_FORCED_REFRESH_MIN_INTERVAL_SECONDS``.
    """
    global _jwks_forced_refresh_at

    now = time.monotonic()
    if (
        _jwks_forced_refresh_at is not None
        and now - _jwks_forced_refresh_at < JWKS_FORCED_REFRESH_MIN_INTERVAL_SECONDS
    ):
        return False
    _jwks_forced_refresh_at = now
    return True


def _get_jwks(*, force: bool = False) -> dict[str, Any]:
    """Fetch and cache Janua JWKS keys for RS256 verification.

    ``force=True`` bypasses the cache (one re-fetch per unknown ``kid``,
    rate-limited by ``_claim_forced_refresh``).
    """
    global _jwks_cache, _jwks_cache_expires_at

    now = time.time()
    if not force and _jwks_cache is not None and now < _jwks_cache_expires_at:
        return _jwks_cache

    response = httpx.get(settings.JANUA_JWKS_URI, timeout=5)
    response.raise_for_status()
    jwks = response.json()
    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise ValueError("Invalid JWKS response")

    _jwks_cache = jwks
    _jwks_cache_expires_at = now + settings.JANUA_JWKS_CACHE_SECONDS
    return jwks


def _find_jwk(jwks: dict[str, Any], kid: str) -> dict[str, Any] | None:
    for key in jwks.get("keys", []):
        if isinstance(key, dict) and key.get("kid") == kid:
            return key
    return None


def _select_jwk(token: str) -> dict[str, Any] | None:
    """Select the JWKS key named by the token's ``kid`` header.

    Janua names its signing key in every token, so a token without ``kid`` is
    rejected. An unknown ``kid`` re-fetches the JWKS once (rate-limited) before
    it is rejected, so a Janua key rotation does not reject valid tokens until
    the cache expires.
    """
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg")
    if alg != _RS256 or not isinstance(kid, str) or not kid:
        return None

    jwk = _find_jwk(_get_jwks(), kid)
    if jwk is None and _claim_forced_refresh():
        logger.info("Token kid not in cached JWKS; re-fetching once (key rotation)")
        jwk = _find_jwk(_get_jwks(force=True), kid)
    return jwk


def _rs256_key(jwk: dict[str, Any]) -> jwt.PyJWK:
    """Bind the selected JWK to RS256.

    A JWK that declares another ``alg``, a ``use`` other than ``sig``, or that
    is not an RSA key is rejected.
    """
    if jwk.get("alg") not in (None, _RS256):
        raise jwt.InvalidKeyError(f"JWKS key alg {jwk.get('alg')!r} is not allowed")
    if jwk.get("use") not in (None, "sig"):
        raise jwt.InvalidKeyError(f"JWKS key use {jwk.get('use')!r} is not 'sig'")
    if jwk.get("kty") != "RSA":
        raise jwt.InvalidKeyError(f"JWKS key kty {jwk.get('kty')!r} is not 'RSA'")
    return jwt.PyJWK(jwk, algorithm=_RS256)


def _decode_jwt(token: str) -> dict[str, Any]:
    """Decode a Janua JWT using RS256 JWKS or explicit HS256 fallback."""
    algorithm = _configured_algorithm()
    audience = _expected_audience()
    issuer = settings.JANUA_JWT_ISSUER or None

    if algorithm == _RS256:
        jwk = _select_jwk(token)
        if not jwk:
            raise jwt.InvalidKeyError("No matching JWKS key")
        # The algorithm is pinned here, never taken from the JWK or the token.
        return cast(dict[str, Any], jwt.decode(
            token,
            _rs256_key(jwk),
            algorithms=[_RS256],
            audience=audience,
            issuer=issuer,
            leeway=JWT_LEEWAY_SECONDS,
            options=_decode_options(audience),
        ))

    if algorithm.startswith("HS"):
        return cast(dict[str, Any], jwt.decode(
            token,
            settings.JANUA_JWT_SECRET,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
            leeway=JWT_LEEWAY_SECONDS,
            options=_decode_options(audience),
        ))

    raise jwt.InvalidAlgorithmError(f"Unsupported Janua JWT algorithm: {algorithm}")


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
    except (PyJWTError, ValueError, ValidationError, httpx.HTTPError):
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


async def require_write_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> User:
    """
    FastAPI dependency guarding mutating endpoints (ingestion, interactions).

    Accepts either:
    - A service API key in the ``X-API-Key`` header matching
      ``settings.INGEST_API_KEY`` (used by the scheduled ingestion CronJob), or
    - A valid Janua Bearer token (any authenticated user).

    Raises HTTPException 401 when neither credential is presented or valid.
    When ``AUTH_ENABLED`` is false (local development), the Janua path falls
    back to the standard dev mock user, so unauthenticated local calls work.
    """
    if (
        settings.INGEST_API_KEY
        and x_api_key
        and secrets.compare_digest(x_api_key, settings.INGEST_API_KEY)
    ):
        return User(
            id="ingest-service",
            email="ingest-service@almanac.solar",
            roles=["service"],
            permissions=["ingest"],
        )

    return await get_current_user(credentials)


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
