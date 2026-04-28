"""
Janua Authentication Integration for Bloom Scroll

Provides JWT verification and user extraction for API endpoints.
Tokens are issued by Janua (MADFAM's centralized auth service).
"""


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

# Security scheme for JWT Bearer tokens
security = HTTPBearer(auto_error=False)


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


def verify_token(token: str) -> TokenPayload | None:
    """
    Verify a Janua JWT token.

    Args:
        token: JWT access token from Janua

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JANUA_JWT_SECRET,
            algorithms=[settings.JANUA_JWT_ALGORITHM],
            options={"verify_exp": True},
        )

        return TokenPayload(
            sub=payload.get("sub"),
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            org_id=payload.get("org_id"),
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            iss=payload.get("iss", "janua"),
        )
    except JWTError:
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


def require_role(required_role: str):
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


def require_permission(required_permission: str):
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
