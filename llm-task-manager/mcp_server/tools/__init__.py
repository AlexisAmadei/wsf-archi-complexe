"""
MCP Tools package.

All tools are registered via @mcp.tool() decorators
and auto-imported by mcp_server/server.py.

Tools organized by domain:
- project_tools: Project management (2 tools)
- epic_tools: Epic management (5 tools)
- story_tools: Story management with BR-01/BR-02 (6 tools)
- sprint_tools: Sprint management with BR-03/BR-04 (6 tools)
- comment_tools: Polymorphic comments (2 tools)
- document_tools: Document management with templates (5 tools)
- ticket_tools: Ticket (sub-task) management with BR-02 (8 tools)

Total: 34 tools
"""
