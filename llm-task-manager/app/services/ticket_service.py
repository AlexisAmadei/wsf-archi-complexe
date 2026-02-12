"""
Ticket service implementing business logic for tickets (sub-tasks).

Handles CRUD, soft-delete / restore, and implements:
- BR-02: Status transition state-machine (same as stories)
- Deletion rule: Only tickets in backlog or todo can be deleted
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules import BusinessRulesEngine
from app.exceptions import BusinessRuleViolation, NotFoundError
from app.models.story import Story
from app.models.ticket import Ticket, TicketStatus
from app.schemas.ticket import TicketCreate, TicketList, TicketResponse, TicketUpdate


class TicketService:
    """Service for managing tickets with business rules enforcement."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rules = BusinessRulesEngine()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, data: TicketCreate) -> Ticket:
        """
        Create a new ticket.

        Args:
            data: Ticket creation data

        Returns:
            Created ticket (status: backlog)

        Raises:
            NotFoundError: If parent story not found
        """
        # Verify parent story exists
        story_result = await self.db.execute(
            select(Story).where(Story.id == data.story_id)
        )
        if not story_result.scalar_one_or_none():
            raise NotFoundError(f"Story with id '{data.story_id}' not found")

        ticket = Ticket(
            id=f"ticket_{uuid.uuid4().hex[:12]}",
            story_id=data.story_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            assignee=data.assignee,
            status=TicketStatus.BACKLOG,
        )

        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def get(self, ticket_id: str) -> Ticket:
        """
        Get a ticket by ID (including archived).

        Raises:
            NotFoundError: If ticket not found
        """
        result = await self.db.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError(f"Ticket with id '{ticket_id}' not found")
        return ticket

    async def update(self, ticket_id: str, data: TicketUpdate) -> Ticket:
        """
        Update ticket metadata (not status – use transition_status).

        Raises:
            NotFoundError: If ticket not found
        """
        ticket = await self.get(ticket_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ticket, field, value)
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    # ------------------------------------------------------------------
    # BR-02: status transition
    # ------------------------------------------------------------------

    async def transition_status(self, ticket_id: str, new_status: str) -> Ticket:
        """
        Transition a ticket to a new status.

        Uses the same BR-02 state-machine as stories:
          backlog → todo → in_progress → in_review → done

        Raises:
            NotFoundError: If ticket not found
            BusinessRuleViolation: If transition is invalid
        """
        ticket = await self.get(ticket_id)

        # Re-use the shared rules engine (same state-machine)
        self.rules.validate_transition(ticket.status, new_status)

        ticket.status = new_status
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    # ------------------------------------------------------------------
    # Soft-delete & restore
    # ------------------------------------------------------------------

    async def delete(self, ticket_id: str) -> None:
        """
        Soft-delete (archive) a ticket.

        A ticket can only be deleted if its status is backlog or todo.

        Raises:
            NotFoundError: If ticket not found
            BusinessRuleViolation: If ticket is in_progress / in_review / done
        """
        ticket = await self.get(ticket_id)

        if ticket.status not in (TicketStatus.BACKLOG, TicketStatus.TODO):
            raise BusinessRuleViolation(
                f"Cannot delete ticket in status '{ticket.status}'. "
                "Only tickets in 'backlog' or 'todo' can be deleted."
            )

        ticket.is_archived = True
        await self.db.commit()
        await self.db.refresh(ticket)

    async def restore(self, ticket_id: str) -> Ticket:
        """
        Restore a previously archived ticket.

        Raises:
            NotFoundError: If ticket not found
            BusinessRuleViolation: If ticket is not archived
        """
        ticket = await self.get(ticket_id)

        if not ticket.is_archived:
            raise BusinessRuleViolation(
                f"Ticket '{ticket_id}' is not archived – nothing to restore."
            )

        ticket.is_archived = False
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    # ------------------------------------------------------------------
    # Listing & search
    # ------------------------------------------------------------------

    async def list(
        self,
        story_id: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> TicketList:
        """
        List tickets with optional filters and pagination.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        query = select(Ticket)
        count_query = select(func.count()).select_from(Ticket)

        if not include_archived:
            query = query.where(Ticket.is_archived == False)  # noqa: E712
            count_query = count_query.where(Ticket.is_archived == False)  # noqa: E712

        if story_id:
            query = query.where(Ticket.story_id == story_id)
            count_query = count_query.where(Ticket.story_id == story_id)

        if status:
            query = query.where(Ticket.status == status)
            count_query = count_query.where(Ticket.status == status)

        if assignee:
            query = query.where(Ticket.assignee == assignee)
            count_query = count_query.where(Ticket.assignee == assignee)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(Ticket.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        tickets = result.scalars().all()

        return TicketList(
            tickets=[TicketResponse.model_validate(t) for t in tickets],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def search(
        self,
        keyword: str,
        story_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> TicketList:
        """Search tickets by keyword in title and description."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        pattern = f"%{keyword}%"
        base_filter = or_(
            Ticket.title.ilike(pattern),
            Ticket.description.ilike(pattern),
        )

        query = select(Ticket).where(base_filter).where(Ticket.is_archived == False)  # noqa: E712
        count_query = (
            select(func.count())
            .select_from(Ticket)
            .where(base_filter)
            .where(Ticket.is_archived == False)  # noqa: E712
        )

        if story_id:
            query = query.where(Ticket.story_id == story_id)
            count_query = count_query.where(Ticket.story_id == story_id)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(Ticket.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        tickets = result.scalars().all()

        return TicketList(
            tickets=[TicketResponse.model_validate(t) for t in tickets],
            total=total,
            page=page,
            page_size=page_size,
        )
