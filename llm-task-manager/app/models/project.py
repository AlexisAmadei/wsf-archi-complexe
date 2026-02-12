"""
Project model.

A project is the top-level container for epics, sprints, and documents.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.epic import Epic
    from app.models.sprint import Sprint


class Project(Base):
    """Project model - top-level container for agile project management."""
    
    __tablename__ = "projects"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    epics: Mapped[list["Epic"]] = relationship(
        "Epic",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    sprints: Mapped[list["Sprint"]] = relationship(
        "Sprint",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"
