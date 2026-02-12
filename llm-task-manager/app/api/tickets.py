"""
Ticket API endpoints.

Provides CRUD, status transitions (BR-02), soft-delete / restore,
search and filtering for tickets (sub-tasks of stories).
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DBSession
from app.schemas.ticket import (
    TicketCreate,
    TicketList,
    TicketResponse,
    TicketStatusTransition,
    TicketUpdate,
)
from app.services.ticket_service import TicketService

router = APIRouter()


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(data: TicketCreate, db: DBSession) -> TicketResponse:
    """Create a new ticket (sub-task) within a story."""
    service = TicketService(db)
    ticket = await service.create(data)
    return TicketResponse.model_validate(ticket)


@router.get("/search", response_model=TicketList)
async def search_tickets(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search keyword"),
    story_id: str | None = Query(None, description="Filter by story ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> TicketList:
    """Search tickets by keyword in title and description."""
    service = TicketService(db)
    return await service.search(keyword=q, story_id=story_id, page=page, page_size=page_size)


@router.get("", response_model=TicketList)
async def list_tickets(
    db: DBSession,
    story_id: str | None = Query(None, description="Filter by story ID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    assignee: str | None = Query(None, description="Filter by assignee"),
    include_archived: bool = Query(False, description="Include archived tickets"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> TicketList:
    """List tickets with optional filters and pagination."""
    service = TicketService(db)
    return await service.list(
        story_id=story_id,
        status=status_filter,
        assignee=assignee,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: DBSession) -> TicketResponse:
    """Get a ticket by ID."""
    service = TicketService(db)
    ticket = await service.get(ticket_id)
    return TicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: str, data: TicketUpdate, db: DBSession) -> TicketResponse:
    """Update a ticket (partial update). Use /transition for status changes."""
    service = TicketService(db)
    ticket = await service.update(ticket_id, data)
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/transition", response_model=TicketResponse)
async def transition_ticket_status(
    ticket_id: str, data: TicketStatusTransition, db: DBSession
) -> TicketResponse:
    """
    Transition a ticket to a new status.

    Follows BR-02 state machine:
    - backlog → todo
    - todo → in_progress | backlog
    - in_progress → in_review | todo
    - in_review → done | in_progress
    - done → (terminal)
    """
    service = TicketService(db)
    ticket = await service.transition_status(ticket_id, data.new_status)
    return TicketResponse.model_validate(ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: str, db: DBSession) -> None:
    """
    Soft-delete (archive) a ticket.

    Only tickets in 'backlog' or 'todo' status can be deleted.
    """
    service = TicketService(db)
    await service.delete(ticket_id)


@router.post("/{ticket_id}/restore", response_model=TicketResponse)
async def restore_ticket(ticket_id: str, db: DBSession) -> TicketResponse:
    """Restore a previously archived ticket."""
    service = TicketService(db)
    ticket = await service.restore(ticket_id)
    return TicketResponse.model_validate(ticket)
