"""
Authentication middleware for MCP server.

Validates JWT Bearer tokens for SSE connections and tool calls.
"""

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security import verify_token


# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_jwt_token(request: Request) -> dict:
    """
    Verify JWT token from Authorization header.

    Args:
        request: FastAPI request object

    Returns:
        Decoded JWT payload

    Raises:
        HTTPException: If token is missing or invalid
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check Bearer scheme
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token
    token = auth_header.replace("Bearer ", "")
    
    # Verify token
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_user(request: Request) -> dict:
    """
    Get current authenticated user from JWT token.

    This dependency can be used in MCP tools to access user information.

    Args:
        request: FastAPI request object

    Returns:
        User information from JWT payload (sub, role, permissions, etc.)
    """
    payload = await verify_jwt_token(request)
    return {
        "user_id": payload.get("sub"),
        "role": payload.get("role", "contributor"),
        "permissions": payload.get("permissions", []),
    }
