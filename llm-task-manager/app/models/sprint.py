"""
Sprint model.

A sprint is a time-boxed iteration for completing stories.
Implements BR-03 (unique active sprint per story) and BR-04 (sprint closure rules).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.story import Story


class SprintStatus(str):
    """Sprint status enumeration."""
    PLANNING = "planning"
    ACTIVE = "active"
    CLOSED = "closed"


# Association table for many-to-many relationship between Story and Sprint
# BR-03: A story can only be in ONE active sprint at a time (enforced by unique index)
story_sprint = Table(
    "story_sprint",
    Base.metadata,
    Column("story_id", String(36), ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True),
    Column("sprint_id", String(36), ForeignKey("sprints.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), default=datetime.utcnow, nullable=False),
    # Denormalized sprint status for BR-03 partial index
    Column("sprint_status", String(20), nullable=False, index=True),
)

# BR-03: Unique index to ensure a story can only be in one active sprint
# This is a partial unique index (WHERE sprint.status = 'active')
# PostgreSQL-specific - will be created in Alembic migration
# CREATE UNIQUE INDEX idx_story_active_sprint ON story_sprint (story_id) 
# WHERE sprint_id IN (SELECT id FROM sprints WHERE status = 'active')


class Sprint(Base):
    """Sprint model - time-boxed iteration with unique active sprint constraint."""
    
    __tablename__ = "sprints"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Foreign keys
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(
        String(20),
        default=SprintStatus.PLANNING,
        nullable=False,
        index=True
    )
    
    # Sprint timeline
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="sprints")
    
    stories: Mapped[list["Story"]] = relationship(
        "Story",
        secondary=story_sprint,
        back_populates="sprints"
    )
    
    def __repr__(self) -> str:
        return f"<Sprint(id={self.id}, name={self.name}, status={self.status})>"
