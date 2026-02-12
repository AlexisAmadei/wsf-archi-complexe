"""
MCP Tools for Ticket management.

Tickets are sub-tasks of Stories – the most granular work item.
Implements BR-02 (status state-machine) and soft-delete rules.

Tools:
- create_ticket: Create a new ticket under a story
- get_ticket: Get ticket details
- update_ticket: Update ticket metadata
- move_ticket: Transition ticket status (BR-02)
- delete_ticket: Soft-delete (archive) a ticket
- restore_ticket: Restore an archived ticket
- list_tickets: List / filter tickets
- search_tickets: Search tickets by keyword
"""

from app.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate
from mcp_server.server import mcp
from mcp_server.shared_services import get_ticket_service, serialize_response


@mcp.tool()
async def create_ticket(
    story_id: str,
    title: str,
    description: str = "",
    priority: str = "medium",
    assignee: str | None = None,
) -> str:
    """Create a new ticket (sub-task) in a story.

    Use this tool when the user wants to:
    - Decompose a story into granular technical tasks
    - Add a bug or chore to a story

    Args:
        story_id: The ID of the parent story (required)
        title: Short title for the ticket, 3-200 chars (required)
        description: Detailed description in markdown (optional)
        priority: Priority – low, medium, high, critical (default: medium)
        assignee: Person assigned to the ticket (optional)

    Returns:
        JSON with created ticket details (status starts at backlog)
    """
    async with get_ticket_service() as service:
        ticket = await service.create(
            TicketCreate(
                story_id=story_id,
                title=title,
                description=description or None,
                priority=priority,
                assignee=assignee,
            )
        )
        return serialize_response(TicketResponse.model_validate(ticket))


@mcp.tool()
async def get_ticket(ticket_id: str) -> str:
    """Get detailed information about a ticket.

    Args:
        ticket_id: The ID of the ticket to retrieve (required)

    Returns:
        JSON with ticket details
    """
    async with get_ticket_service() as service:
        ticket = await service.get(ticket_id)
        return serialize_response(TicketResponse.model_validate(ticket))


@mcp.tool()
async def update_ticket(
    ticket_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
) -> str:
    """Update a ticket's metadata.

    Note: To change status, use move_ticket instead.

    Args:
        ticket_id: The ID of the ticket to update (required)
        title: New title (optional)
        description: New description (optional)
        priority: New priority – low, medium, high, critical (optional)
        assignee: New assignee (optional)

    Returns:
        JSON with updated ticket details
    """
    async with get_ticket_service() as service:
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if priority is not None:
            update_data["priority"] = priority
        if assignee is not None:
            update_data["assignee"] = assignee

        ticket = await service.update(ticket_id, TicketUpdate(**update_data))
        return serialize_response(TicketResponse.model_validate(ticket))


@mcp.tool()
async def move_ticket(ticket_id: str, target_status: str) -> str:
    """Move a ticket to a new status (BR-02 state machine).

    Allowed transitions:
    - backlog → todo
    - todo → in_progress | backlog
    - in_progress → in_review | todo
    - in_review → done | in_progress
    - done → (terminal, no further transitions)

    Args:
        ticket_id: The ID of the ticket (required)
        target_status: Target status – backlog, todo, in_progress, in_review, done (required)

    Returns:
        JSON with updated ticket showing the new status
    """
    async with get_ticket_service() as service:
        ticket = await service.transition_status(ticket_id, target_status)
        return serialize_response(TicketResponse.model_validate(ticket))


@mcp.tool()
async def delete_ticket(ticket_id: str) -> str:
    """Soft-delete (archive) a ticket.

    A ticket can only be deleted if its status is 'backlog' or 'todo'.
    Tickets in 'in_progress', 'in_review', or 'done' cannot be deleted.

    Args:
        ticket_id: The ID of the ticket to delete (required)

    Returns:
        Confirmation message
    """
    async with get_ticket_service() as service:
        await service.delete(ticket_id)
        return '{"message": "Ticket archived successfully"}'


@mcp.tool()
async def restore_ticket(ticket_id: str) -> str:
    """Restore a previously archived (soft-deleted) ticket.

    Args:
        ticket_id: The ID of the ticket to restore (required)

    Returns:
        JSON with restored ticket details
    """
    async with get_ticket_service() as service:
        ticket = await service.restore(ticket_id)
        return serialize_response(TicketResponse.model_validate(ticket))


@mcp.tool()
async def list_tickets(
    story_id: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List tickets with optional filters.

    Use this tool to see all sub-tasks of a story or filter by status/assignee.

    Args:
        story_id: Filter by story ID (optional)
        status: Filter by status – backlog, todo, in_progress, in_review, done (optional)
        assignee: Filter by assignee name (optional)
        include_archived: Whether to include archived tickets (default: false)
        page: Page number, starting from 1 (default: 1)
        page_size: Number of tickets per page (default: 50, max: 100)

    Returns:
        JSON with list of tickets and pagination info
    """
    async with get_ticket_service() as service:
        result = await service.list(
            story_id=story_id,
            status=status,
            assignee=assignee,
            include_archived=include_archived,
            page=page,
            page_size=page_size,
        )
        return serialize_response(result)


@mcp.tool()
async def search_tickets(keyword: str, story_id: str | None = None) -> str:
    """Search tickets by keyword in title and description.

    Args:
        keyword: Search term (required)
        story_id: Optional filter by story ID

    Returns:
        JSON with matching tickets
    """
    async with get_ticket_service() as service:
        result = await service.search(keyword=keyword, story_id=story_id)
        return serialize_response(result)
