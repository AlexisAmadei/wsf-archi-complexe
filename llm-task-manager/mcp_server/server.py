"""
MCP Server - Standalone server for LLM Task Manager.

This server is completely independent from the FastAPI REST API.
Both share the same business logic services and database connection.

Exposes project management tools via the Model Context Protocol (MCP)
using SSE transport for communication with LLM clients
(Claude Desktop, Cursor, etc.).
"""

import os

from mcp.server.fastmcp import FastMCP

# Get port from environment (Cloud Run sets PORT)
port = int(os.environ.get("PORT", "8001"))

# Create MCP server instance
mcp = FastMCP(
    "llm-task-manager",
    instructions=(
        "LLM Task Manager - Agile project management via MCP. "
        "Manage projects, epics, stories, sprints, comments, and documents. "
        "Implements Fibonacci story points (BR-01), status state machine (BR-02), "
        "unique active sprint per story (BR-03), and sprint closure rules (BR-04)."
    ),
    host="0.0.0.0",
    port=port,
)

# Import and register all tools
# Tools are registered via @mcp.tool() decorators in each module
import mcp_server.tools.project_tools  # noqa: F401, E402
import mcp_server.tools.epic_tools  # noqa: F401, E402
import mcp_server.tools.story_tools  # noqa: F401, E402
import mcp_server.tools.sprint_tools  # noqa: F401, E402
import mcp_server.tools.comment_tools  # noqa: F401, E402
import mcp_server.tools.document_tools  # noqa: F401, E402
