"""
MCP Tools for Story management.

Implements tools with business rules:
- BR-01: Story points must be Fibonacci values (1, 2, 3, 5, 8, 13, 21)
- BR-02: Story status transitions follow a state machine

Tools:
- create_story: Create a new user story
- get_story: Get story details
- update_story: Update a story
- transition_story_status: Change story status (state machine)
- list_stories: List stories with filters
- search_stories: Search stories by keyword
"""

from app.schemas.story import StoryCreate, StoryResponse, StoryUpdate
from mcp_server.server import mcp
from mcp_server.shared_services import get_story_service, serialize_response


@mcp.tool()
async def create_story(
    epic_id: str,
    title: str,
    description: str = "",
    priority: str = "medium",
    story_points: int | None = None,
    assignee: str | None = None,
) -> str:
    """Create a new user story in an epic.

    Use this tool when the user wants to:
    - Add a new feature or task to an epic
    - Break down an epic into smaller pieces
    - Create a story from a conversation

    Business Rule BR-01: Story points must be Fibonacci values.

    Args:
        epic_id: The ID of the parent epic (required)
        title: Short title for the story (required)
        description: Detailed description in markdown (optional)
        priority: Priority level - one of: low, medium, high, critical (default: medium)
        story_points: Estimate using Fibonacci sequence: 1, 2, 3, 5, 8, 13, 21 (optional)
        assignee: Person assigned to the story (optional)

    Returns:
        JSON with created story details and initial status (backlog)

    Example:
        create_story(
            epic_id="epic_abc123",
            title="Add user authentication",
            description="Implement JWT-based auth with refresh tokens",
            priority="high",
            story_points=5
        )
    """
    async with get_story_service() as service:
        story = await service.create(
            StoryCreate(
                epic_id=epic_id,
                title=title,
                description=description or None,
                priority=priority,
                story_points=story_points,
                assignee=assignee,
            )
        )
        return serialize_response(StoryResponse.model_validate(story))


@mcp.tool()
async def get_story(story_id: str) -> str:
    """Get detailed information about a story.

    Use this tool when the user wants to:
    - View details of a specific story
    - Check the current status and assignee
    - Get story points and priority information

    Args:
        story_id: The ID of the story to retrieve (required)

    Returns:
        JSON with story details (id, title, status, priority, story_points, assignee, etc.)
    """
    async with get_story_service() as service:
        story = await service.get(story_id)
        return serialize_response(StoryResponse.model_validate(story))


@mcp.tool()
async def update_story(
    story_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    story_points: int | None = None,
    assignee: str | None = None,
) -> str:
    """Update an existing story.

    Use this tool when the user wants to:
    - Change story details (title, description)
    - Update priority or story points
    - Assign or reassign a story
    
    Note: To change status, use transition_story_status instead.
    Business Rule BR-01: Story points must be Fibonacci values.

    Args:
        story_id: The ID of the story to update (required)
        title: New title (optional)
        description: New description (optional)
        priority: New priority - one of: low, medium, high, critical (optional)
        story_points: New estimate - Fibonacci: 1, 2, 3, 5, 8, 13, 21 (optional)
        assignee: New assignee (optional)

    Returns:
        JSON with updated story details
    """
    async with get_story_service() as service:
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if priority is not None:
            update_data["priority"] = priority
        if story_points is not None:
            update_data["story_points"] = story_points
        if assignee is not None:
            update_data["assignee"] = assignee

        story = await service.update(story_id, StoryUpdate(**update_data))
        return serialize_response(StoryResponse.model_validate(story))


@mcp.tool()
async def transition_story_status(story_id: str, new_status: str) -> str:
    """Change the status of a story following the state machine.

    Use this tool when the user wants to:
    - Move a story to the next stage
    - Start working on a story
    - Mark a story as done
    - Send a story back to a previous stage

    Business Rule BR-02: Allowed transitions:
    - backlog → todo
    - todo → in_progress, backlog
    - in_progress → in_review, todo
    - in_review → done, in_progress
    - done → (terminal state, no transitions)

    Args:
        story_id: The ID of the story (required)
        new_status: Target status - one of: backlog, todo, in_progress, in_review, done (required)

    Returns:
        JSON with updated story details showing new status

    Example:
        transition_story_status(story_id="story_abc123", new_status="in_progress")
    """
    async with get_story_service() as service:
        story = await service.transition_status(story_id, new_status)
        return serialize_response(StoryResponse.model_validate(story))


@mcp.tool()
async def list_stories(
    epic_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    sprint_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List stories with optional filters.

    Use this tool when the user wants to:
    - See all stories in an epic
    - Filter stories by status, priority, or assignee
    - View stories assigned to a sprint
    - Get an overview of the backlog

    Args:
        epic_id: Filter by epic ID (optional)
        status: Filter by status - backlog, todo, in_progress, in_review, done (optional)
        priority: Filter by priority - low, medium, high, critical (optional)
        assignee: Filter by assignee name (optional)
        sprint_id: Filter by sprint ID (optional)
        page: Page number, starting from 1 (default: 1)
        page_size: Number of stories per page (default: 50, max: 100)

    Returns:
        JSON with list of stories and pagination info
    """
    async with get_story_service() as service:
        result = await service.list(
            epic_id=epic_id,
            status=status,
            priority=priority,
            assignee=assignee,
            sprint_id=sprint_id,
            page=page,
            page_size=page_size,
        )
        return serialize_response(result)


@mcp.tool()
async def search_stories(keyword: str, epic_id: str | None = None) -> str:
    """Search stories by keyword in title and description.

    Use this tool when the user wants to:
    - Find stories matching a specific term
    - Search for stories related to a feature
    - Locate a story by partial name

    Args:
        keyword: Search term to look for in title and description (required)
        epic_id: Optional filter by epic ID

    Returns:
        JSON with list of matching stories
    """
    async with get_story_service() as service:
        result = await service.search(keyword=keyword, epic_id=epic_id)
        return serialize_response(result)
