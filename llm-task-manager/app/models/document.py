"""
Document model.

Documents store project-related documentation using templates.
Supports Problem Statement, Product Vision, Technical Decision Record, Sprint Retrospective.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class DocumentTemplateType(str):
    """Document template types."""
    PROBLEM_STATEMENT = "problem_statement"
    PRODUCT_VISION = "product_vision"
    TECHNICAL_DECISION = "technical_decision"
    SPRINT_RETROSPECTIVE = "sprint_retrospective"


class Document(Base):
    """Document model - project documentation with templates."""
    
    __tablename__ = "documents"
    
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
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    template_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )
    
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
    project: Mapped["Project"] = relationship("Project", back_populates="documents")
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, template_type={self.template_type})>"
