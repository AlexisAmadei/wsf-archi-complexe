"""
Story schemas for API request/response validation.

Implements BR-01 (Fibonacci story points) validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.story import StoryPriority, StoryStatus


# BR-01: Fibonacci values for story points
FIBONACCI_VALUES = [None, 1, 2, 3, 5, 8, 13, 21]


class StoryCreate(BaseModel):
    """Schema for creating a new story."""
    epic_id: str = Field(..., description="Parent epic ID")
    title: str = Field(..., min_length=1, max_length=500, description="Story title")
    description: str | None = Field(None, description="Story description")
    priority: str = Field(default=StoryPriority.MEDIUM, description="Story priority")
    story_points: int | None = Field(None, ge=1, le=21, description="Story points (Fibonacci: 1,2,3,5,8,13,21)")
    assignee: str | None = Field(None, max_length=255, description="Assigned to")
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority is one of the allowed values."""
        allowed = [StoryPriority.LOW, StoryPriority.MEDIUM, StoryPriority.HIGH, StoryPriority.CRITICAL]
        if v not in allowed:
            raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: int | None) -> int | None:
        """BR-01: Validate story points are Fibonacci values."""
        if v is not None and v not in FIBONACCI_VALUES:
            raise ValueError(f"Story points must be one of: {', '.join(map(str, [x for x in FIBONACCI_VALUES if x is not None]))}")
        return v


class StoryUpdate(BaseModel):
    """Schema for updating a story."""
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = None
    story_points: int | None = Field(None, ge=1, le=21)
    assignee: str | None = Field(None, max_length=255)
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        """Validate priority is one of the allowed values."""
        if v is None:
            return v
        allowed = [StoryPriority.LOW, StoryPriority.MEDIUM, StoryPriority.HIGH, StoryPriority.CRITICAL]
        if v not in allowed:
            raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: int | None) -> int | None:
        """BR-01: Validate story points are Fibonacci values."""
        if v is not None and v not in FIBONACCI_VALUES:
            raise ValueError(f"Story points must be one of: {', '.join(map(str, [x for x in FIBONACCI_VALUES if x is not None]))}")
        return v


class StoryStatusTransition(BaseModel):
    """Schema for transitioning story status (BR-02)."""
    new_status: str = Field(..., description="New status to transition to")
    
    @field_validator("new_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of the allowed values."""
        allowed = [
            StoryStatus.BACKLOG,
            StoryStatus.TODO,
            StoryStatus.IN_PROGRESS,
            StoryStatus.IN_REVIEW,
            StoryStatus.DONE
        ]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


class StoryResponse(BaseModel):
    """Schema for story API response."""
    id: str
    epic_id: str
    title: str
    description: str | None
    status: str
    priority: str
    story_points: int | None
    assignee: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class StoryList(BaseModel):
    """Schema for listing stories with pagination."""
    stories: list[StoryResponse]
    total: int
    page: int = 1
    page_size: int = 50
