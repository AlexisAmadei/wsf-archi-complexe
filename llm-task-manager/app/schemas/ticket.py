"""
Ticket schemas for API request/response validation.

Implements BR-02 (status transitions) validation for tickets.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.ticket import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    """Schema for creating a new ticket (sub-task of a story)."""
    story_id: str = Field(..., description="Parent story ID")
    title: str = Field(..., min_length=3, max_length=200, description="Ticket title")
    description: str | None = Field(None, description="Ticket description")
    priority: str = Field(default=TicketPriority.MEDIUM, description="Ticket priority")
    assignee: str | None = Field(None, max_length=255, description="Assigned to")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = [TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH, TicketPriority.CRITICAL]
        if v not in allowed:
            raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
        return v


class TicketUpdate(BaseModel):
    """Schema for updating a ticket."""
    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = None
    priority: str | None = None
    assignee: str | None = Field(None, max_length=255)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = [TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH, TicketPriority.CRITICAL]
        if v not in allowed:
            raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
        return v


class TicketStatusTransition(BaseModel):
    """Schema for transitioning ticket status (BR-02)."""
    new_status: str = Field(..., description="Target status")

    @field_validator("new_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = [
            TicketStatus.BACKLOG,
            TicketStatus.TODO,
            TicketStatus.IN_PROGRESS,
            TicketStatus.IN_REVIEW,
            TicketStatus.DONE,
        ]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


class TicketResponse(BaseModel):
    """Schema for ticket API response."""
    id: str
    story_id: str
    title: str
    description: str | None
    status: str
    priority: str
    assignee: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketList(BaseModel):
    """Schema for listing tickets with pagination."""
    tickets: list[TicketResponse]
    total: int
    page: int = 1
    page_size: int = 50
