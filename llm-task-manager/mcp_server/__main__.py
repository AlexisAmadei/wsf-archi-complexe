"""
Entry point for the standalone MCP server.

Usage:
    python -m mcp_server                     # Default: stdio transport
    python -m mcp_server --transport sse     # SSE transport (for remote/Cloud Run)
    python -m mcp_server --sse               # Shorthand for SSE

Environment variables:
    PORT: Port for SSE transport (default: 8001, Cloud Run sets this)
    DATABASE_URL: PostgreSQL connection string
    JWT_SECRET_KEY: JWT secret key
    MCP_DISABLE_AUTH: Set to "true" to disable JWT auth (dev only)

The MCP server runs independently from the FastAPI REST API.
Both share the same services and database.
"""

import os
import sys


def main():
    """Run the MCP server."""
    from mcp_server.server import mcp

    # Determine transport mode
    transport = "stdio"

    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    if "--sse" in sys.argv:
        transport = "sse"

    print(f"Starting LLM Task Manager MCP Server (transport: {transport})")

    if transport == "sse" and os.environ.get("MCP_DISABLE_AUTH", "false").lower() != "true":
        # For SSE transport with auth: run with custom ASGI wrapper
        _run_with_auth(mcp)
    else:
        # For stdio or when auth is disabled: run normally
        mcp.run(transport=transport)


def _run_with_auth(mcp):
    """Run MCP server with JWT authentication middleware wrapping the SSE app."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    from mcp_server.auth import verify_jwt_token

    class AuthMiddleware(BaseHTTPMiddleware):
        """Validates JWT Bearer token on every SSE/MCP request."""

        async def dispatch(self, request: Request, call_next):
            if request.method == "OPTIONS":
                return await call_next(request)

            try:
                await verify_jwt_token(request)
            except Exception:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized", "detail": "Invalid or missing Bearer token"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return await call_next(request)

    # Get the underlying Starlette SSE app from FastMCP
    sse_app = mcp.sse_app()

    # Wrap it with auth middleware
    app = Starlette(
        routes=[Mount("/", app=sse_app)],
        middleware=[Middleware(AuthMiddleware)],
    )

    port = int(os.environ.get("PORT", "8001"))
    print(f"JWT authentication enabled on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
