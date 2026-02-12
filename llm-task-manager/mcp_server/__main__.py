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

The MCP server runs independently from the FastAPI REST API.
Both share the same services and database.
"""

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
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
