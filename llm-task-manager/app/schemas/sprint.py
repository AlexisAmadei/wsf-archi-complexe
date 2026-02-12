"""
Sprint schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.sprint import SprintStatus


class SprintCreate(BaseModel):
    """Schema for creating a new sprint."""
    project_id: str = Field(..., description="Parent project ID")
    name: str = Field(..., min_length=1, max_length=255, description="Sprint name")
    goal: str | None = Field(None, description="Sprint goal")
    start_date: datetime | None = Field(None, description="Sprint start date")
    end_date: datetime | None = Field(None, description="Sprint end date")


class SprintUpdate(BaseModel):
    """Schema for updating a sprint."""
    name: str | None = Field(None, min_length=1, max_length=255)
    goal: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class SprintResponse(BaseModel):
    """Schema for sprint API response."""
    id: str
    project_id: str
    name: str
    goal: str | None
    status: str
    start_date: datetime | None
    end_date: datetime | None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class SprintList(BaseModel):
    """Schema for listing sprints with pagination."""
    sprints: list[SprintResponse]
    total: int
    page: int = 1
    page_size: int = 50


class SprintStoryAssignment(BaseModel):
    """Schema for assigning a story to a sprint (BR-03)."""
    story_id: str = Field(..., description="Story ID to assign to sprint")


class SprintClosureRequest(BaseModel):
    """Schema for closing a sprint (BR-04)."""
    force: bool = Field(default=False, description="Force close even with in-progress stories")
