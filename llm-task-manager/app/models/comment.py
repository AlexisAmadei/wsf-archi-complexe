"""
Comment model.

Comments are polymorphic - they can be attached to any entity.
Uses entity_type + entity_id pattern for polymorphic association.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommentEntityType(str):
    """Entity types that can have comments."""
    EPIC = "epic"
    STORY = "story"
    SPRINT = "sprint"
    DOCUMENT = "document"


class Comment(Base):
    """Comment model - polymorphic comments for any entity."""
    
    __tablename__ = "comments"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Polymorphic association fields
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )
    
    # Core fields
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, entity_type={self.entity_type}, entity_id={self.entity_id})>"
