"""
Epic schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.epic import EpicStatus


class EpicCreate(BaseModel):
    """Schema for creating a new epic."""
    project_id: str = Field(..., description="Parent project ID")
    title: str = Field(..., min_length=1, max_length=500, description="Epic title")
    description: str | None = Field(None, description="Epic description")
    status: str = Field(default=EpicStatus.TODO, description="Epic status")
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate epic status is one of the allowed values."""
        allowed = [EpicStatus.TODO, EpicStatus.IN_PROGRESS, EpicStatus.DONE]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


class EpicUpdate(BaseModel):
    """Schema for updating an epic."""
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate epic status is one of the allowed values."""
        if v is None:
            return v
        allowed = [EpicStatus.TODO, EpicStatus.IN_PROGRESS, EpicStatus.DONE]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


class EpicResponse(BaseModel):
    """Schema for epic API response."""
    id: str
    project_id: str
    title: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class EpicList(BaseModel):
    """Schema for listing epics with pagination."""
    epics: list[EpicResponse]
    total: int
    page: int = 1
    page_size: int = 50
