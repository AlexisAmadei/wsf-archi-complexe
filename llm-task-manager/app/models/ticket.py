"""
Ticket model.

A ticket is a sub-task of a story – the most granular work item.
Implements BR-02 (status transitions) and soft-delete with archiving.

Tickets inherit the same status state-machine as stories:
  backlog → todo → in_progress → in_review → done
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.story import Story


class TicketStatus(str):
    """Ticket status enumeration – mirrors StoryStatus for BR-02."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TicketPriority(str):
    """Ticket priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    """Ticket model – granular sub-task linked to a story."""

    __tablename__ = "tickets"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign keys
    story_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # BR-02: status with state-machine validation (application layer)
    status: Mapped[str] = mapped_column(
        String(20),
        default=TicketStatus.BACKLOG,
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True,
    )

    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Soft-delete support
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    story: Mapped["Story"] = relationship("Story", back_populates="tickets")

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, title={self.title}, status={self.status}, archived={self.is_archived})>"
