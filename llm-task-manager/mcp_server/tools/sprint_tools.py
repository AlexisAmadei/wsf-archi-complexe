"""
MCP Tools for Sprint management.

Implements tools with business rules:
- BR-03: A story can only be in one active sprint at a time
- BR-04: Sprint can only be closed if no stories are in progress

Tools:
- create_sprint: Create a new sprint
- start_sprint: Start a sprint (planning → active)
- close_sprint: Close a sprint (active → closed)
- assign_story_to_sprint: Assign a story to a sprint
- remove_story_from_sprint: Remove a story from a sprint
- list_sprints: List sprints with optional filters
"""

from app.schemas.sprint import SprintCreate, SprintResponse
from mcp_server.server import mcp
from mcp_server.shared_services import get_sprint_service, serialize_response


@mcp.tool()
async def create_sprint(
    project_id: str,
    name: str,
    goal: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Create a new sprint in a project.

    Use this tool when the user wants to:
    - Plan a new sprint iteration
    - Set up a time-boxed period for completing stories
    - Organize upcoming work

    Args:
        project_id: The ID of the parent project (required)
        name: Sprint name, e.g. "Sprint 1" (required)
        goal: Sprint goal describing what to achieve (optional)
        start_date: Start date in ISO format YYYY-MM-DD (optional)
        end_date: End date in ISO format YYYY-MM-DD (optional)

    Returns:
        JSON with created sprint details (initial status: planning)
    """
    from datetime import datetime

    parsed_start = datetime.fromisoformat(start_date) if start_date else None
    parsed_end = datetime.fromisoformat(end_date) if end_date else None

    async with get_sprint_service() as service:
        sprint = await service.create(
            SprintCreate(
                project_id=project_id,
                name=name,
                goal=goal or None,
                start_date=parsed_start,
                end_date=parsed_end,
            )
        )
        return serialize_response(SprintResponse.model_validate(sprint))


@mcp.tool()
async def start_sprint(sprint_id: str) -> str:
    """Start a sprint (transition from planning to active).

    Use this tool when the user wants to:
    - Begin a sprint that has been planned
    - Activate a sprint so stories can be worked on
    - Kick off a new iteration

    Only sprints in 'planning' status can be started.

    Args:
        sprint_id: The ID of the sprint to start (required)

    Returns:
        JSON with updated sprint details (status: active)
    """
    async with get_sprint_service() as service:
        sprint = await service.start(sprint_id)
        return serialize_response(SprintResponse.model_validate(sprint))


@mcp.tool()
async def close_sprint(sprint_id: str, force: bool = False) -> str:
    """Close a sprint (transition from active to closed).

    Use this tool when the user wants to:
    - End a sprint iteration
    - Complete a sprint and review results
    - Wrap up current work

    Business Rule BR-04: A sprint can only be closed if no stories 
    are in 'in_progress' or 'in_review' status, unless force=True.

    Args:
        sprint_id: The ID of the sprint to close (required)
        force: Force close even with in-progress stories (default: false)

    Returns:
        JSON with updated sprint details (status: closed)
    """
    async with get_sprint_service() as service:
        sprint = await service.close(sprint_id, force=force)
        return serialize_response(SprintResponse.model_validate(sprint))


@mcp.tool()
async def assign_story_to_sprint(sprint_id: str, story_id: str) -> str:
    """Assign a story to a sprint.

    Use this tool when the user wants to:
    - Add a story to the current sprint
    - Plan which stories to work on in a sprint
    - Move a backlog item into a sprint

    Business Rule BR-03: A story can only be in ONE active sprint at a time.

    Args:
        sprint_id: The ID of the sprint (required)
        story_id: The ID of the story to assign (required)

    Returns:
        Confirmation message
    """
    async with get_sprint_service() as service:
        await service.assign_story(sprint_id, story_id)
        return f"Story {story_id} has been assigned to sprint {sprint_id}"


@mcp.tool()
async def remove_story_from_sprint(sprint_id: str, story_id: str) -> str:
    """Remove a story from a sprint.

    Use this tool when the user wants to:
    - Take a story out of the current sprint
    - Descope a story from the sprint
    - Move a story back to the backlog

    Args:
        sprint_id: The ID of the sprint (required)
        story_id: The ID of the story to remove (required)

    Returns:
        Confirmation message
    """
    async with get_sprint_service() as service:
        await service.remove_story(sprint_id, story_id)
        return f"Story {story_id} has been removed from sprint {sprint_id}"


@mcp.tool()
async def list_sprints(
    project_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List sprints with optional filters.

    Use this tool when the user wants to:
    - See all sprints in a project
    - Find active or closed sprints
    - Get an overview of sprint history

    Args:
        project_id: Filter by project ID (optional)
        status: Filter by status - one of: planning, active, closed (optional)
        page: Page number, starting from 1 (default: 1)
        page_size: Number of sprints per page (default: 50, max: 100)

    Returns:
        JSON with list of sprints and pagination info
    """
    async with get_sprint_service() as service:
        result = await service.list(
            project_id=project_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        return serialize_response(result)
