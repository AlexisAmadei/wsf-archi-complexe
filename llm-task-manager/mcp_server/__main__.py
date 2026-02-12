"""
Entry point for the standalone MCP server.

Usage:
    python -m mcp_server                     # Default: stdio transport
    python -m mcp_server --transport sse     # SSE transport (for remote clients)
    python -m mcp_server --transport stdio   # stdio transport (for local clients)

The MCP server runs independently from the FastAPI REST API.
Both share the same services and database.
"""

import sys

from mcp_server.server import mcp


def main():
    """Run the MCP server."""
    # Default to stdio, but allow SSE via argument
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
