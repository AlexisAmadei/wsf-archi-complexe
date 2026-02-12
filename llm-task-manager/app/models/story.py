"""
Story model.

A user story represents a small, incremental piece of work.
Implements business rules BR-01 (Fibonacci story points) and BR-02 (status transitions).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.epic import Epic
    from app.models.sprint import Sprint
    from app.models.ticket import Ticket


class StoryStatus(str):
    """Story status enumeration for BR-02 state machine."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class StoryPriority(str):
    """Story priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Story(Base):
    """Story model - user story with status transitions and Fibonacci story points."""
    
    __tablename__ = "stories"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Foreign keys
    epic_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("epics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # BR-02: Status with state machine validation (validated in application layer)
    status: Mapped[str] = mapped_column(
        String(20),
        default=StoryStatus.BACKLOG,
        nullable=False,
        index=True
    )
    
    priority: Mapped[str] = mapped_column(
        String(20),
        default=StoryPriority.MEDIUM,
        nullable=False,
        index=True
    )
    
    # BR-01: Story points must be Fibonacci sequence or NULL
    story_points: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    epic: Mapped["Epic"] = relationship("Epic", back_populates="stories")
    
    sprints: Mapped[list["Sprint"]] = relationship(
        "Sprint",
        secondary="story_sprint",
        back_populates="stories"
    )

    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="story",
        cascade="all, delete-orphan",
    )
    
    # Table constraints
    __table_args__ = (
        # BR-01: Story points must be NULL or Fibonacci value
        CheckConstraint(
            "story_points IS NULL OR story_points IN (1, 2, 3, 5, 8, 13, 21)",
            name="ck_story_points_fibonacci"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Story(id={self.id}, title={self.title}, status={self.status})>"
