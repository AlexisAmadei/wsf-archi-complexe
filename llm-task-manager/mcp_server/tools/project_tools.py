"""
MCP Tools for Project management.

Tools:
- create_project: Create a new project
- list_projects: List all projects
"""

from app.schemas.project import ProjectCreate, ProjectResponse
from mcp_server.server import mcp
from mcp_server.shared_services import get_project_service, serialize_response


@mcp.tool()
async def create_project(name: str, description: str = "") -> str:
    """Create a new project.

    Use this tool when the user wants to:
    - Start a new project
    - Create a workspace for organizing epics, stories, and sprints

    Args:
        name: Project name (required)
        description: Project description (optional)

    Returns:
        JSON with created project details including its ID
    """
    async with get_project_service() as service:
        project = await service.create(
            ProjectCreate(name=name, description=description or None)
        )
        return serialize_response(ProjectResponse.model_validate(project))


@mcp.tool()
async def list_projects(page: int = 1, page_size: int = 50) -> str:
    """List all projects.

    Use this tool when the user wants to:
    - See all available projects
    - Find a project by browsing the list
    - Get an overview of existing projects

    Args:
        page: Page number, starting from 1 (default: 1)
        page_size: Number of projects per page (default: 50, max: 100)

    Returns:
        JSON with list of projects and pagination info
    """
    async with get_project_service() as service:
        result = await service.list(page=page, page_size=page_size)
        return serialize_response(result)
