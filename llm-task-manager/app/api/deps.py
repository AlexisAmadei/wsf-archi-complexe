"""
FastAPI dependencies for dependency injection.

Provides database sessions and optional authentication.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import verify_token

# Type alias for database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
) -> dict:
    """
    Validate JWT token and return user information.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        User information from JWT payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": payload.get("sub"),
        "role": payload.get("role", "contributor"),
        "permissions": payload.get("permissions", []),
        "type": payload.get("type"),
    }


# Type alias for authenticated user dependency
CurrentUser = Annotated[dict, Depends(get_current_user)]
