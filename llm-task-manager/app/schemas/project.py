"""
Project schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, description="Project description")


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    """Schema for project API response."""
    id: str
    name: str
    description: str | None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectList(BaseModel):
    """Schema for listing projects with pagination."""
    projects: list[ProjectResponse]
    total: int
    page: int = 1
    page_size: int = 50
