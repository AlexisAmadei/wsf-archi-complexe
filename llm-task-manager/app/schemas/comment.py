"""
Comment schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.comment import CommentEntityType


class CommentCreate(BaseModel):
    """Schema for creating a new comment."""
    entity_type: str = Field(..., description="Type of entity (epic, story, sprint, document)")
    entity_id: str = Field(..., description="ID of the entity")
    content: str = Field(..., min_length=1, description="Comment content")
    author: str = Field(..., min_length=1, max_length=255, description="Comment author")
    
    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type is one of the allowed values."""
        allowed = [
            CommentEntityType.EPIC,
            CommentEntityType.STORY,
            CommentEntityType.SPRINT,
            CommentEntityType.DOCUMENT
        ]
        if v not in allowed:
            raise ValueError(f"Entity type must be one of: {', '.join(allowed)}")
        return v


class CommentResponse(BaseModel):
    """Schema for comment API response."""
    id: str
    entity_type: str
    entity_id: str
    content: str
    author: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class CommentList(BaseModel):
    """Schema for listing comments with pagination."""
    comments: list[CommentResponse]
    total: int
    page: int = 1
    page_size: int = 50
