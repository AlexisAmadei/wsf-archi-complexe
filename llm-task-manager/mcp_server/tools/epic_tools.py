"""
MCP Tools for Epic management.

Tools:
- create_epic: Create a new epic in a project
- get_epic: Get epic details by ID
- update_epic: Update an existing epic
- list_epics: List epics with optional filters
- search_epics: Search epics by keyword
"""

from app.schemas.epic import EpicCreate, EpicResponse, EpicUpdate
from mcp_server.server import mcp
from mcp_server.shared_services import get_epic_service, serialize_response


@mcp.tool()
async def create_epic(
    project_id: str,
    title: str,
    description: str = "",
) -> str:
    """Create a new epic in a project.

    Use this tool when the user wants to:
    - Add a large body of work to a project
    - Create a new feature area or initiative
    - Organize stories under a common theme

    Args:
        project_id: The ID of the parent project (required)
        title: Epic title (required)
        description: Detailed description of the epic (optional)

    Returns:
        JSON with created epic details including its ID and initial status (todo)
    """
    async with get_epic_service() as service:
        epic = await service.create(
            EpicCreate(
                project_id=project_id,
                title=title,
                description=description or None,
            )
        )
        return serialize_response(EpicResponse.model_validate(epic))


@mcp.tool()
async def get_epic(epic_id: str) -> str:
    """Get detailed information about an epic.

    Use this tool when the user wants to:
    - View details of a specific epic
    - Check the status of an epic
    - Get information before updating an epic

    Args:
        epic_id: The ID of the epic to retrieve (required)

    Returns:
        JSON with epic details (id, title, description, status, timestamps)
    """
    async with get_epic_service() as service:
        epic = await service.get(epic_id)
        return serialize_response(EpicResponse.model_validate(epic))


@mcp.tool()
async def update_epic(
    epic_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
) -> str:
    """Update an existing epic.

    Use this tool when the user wants to:
    - Change the title or description of an epic
    - Update the status of an epic (todo, in_progress, done)
    - Modify epic details

    Args:
        epic_id: The ID of the epic to update (required)
        title: New title (optional)
        description: New description (optional)
        status: New status - one of: todo, in_progress, done (optional)

    Returns:
        JSON with updated epic details
    """
    async with get_epic_service() as service:
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = status

        epic = await service.update(epic_id, EpicUpdate(**update_data))
        return serialize_response(EpicResponse.model_validate(epic))


@mcp.tool()
async def list_epics(
    project_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List epics with optional filters.

    Use this tool when the user wants to:
    - See all epics in a project
    - Filter epics by status
    - Browse available epics

    Args:
        project_id: Filter by project ID (optional)
        status: Filter by status - one of: todo, in_progress, done (optional)
        page: Page number, starting from 1 (default: 1)
        page_size: Number of epics per page (default: 50, max: 100)

    Returns:
        JSON with list of epics and pagination info
    """
    async with get_epic_service() as service:
        result = await service.list(
            project_id=project_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        return serialize_response(result)


@mcp.tool()
async def search_epics(keyword: str, project_id: str | None = None) -> str:
    """Search epics by keyword in title and description.

    Use this tool when the user wants to:
    - Find epics matching a specific term
    - Search for epics related to a topic
    - Locate an epic by partial name

    Args:
        keyword: Search term to look for in title and description (required)
        project_id: Optional filter by project ID

    Returns:
        JSON with list of matching epics
    """
    async with get_epic_service() as service:
        result = await service.search(keyword=keyword, project_id=project_id)
        return serialize_response(result)
