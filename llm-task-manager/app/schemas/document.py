"""
Document schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.document import DocumentTemplateType


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""
    project_id: str = Field(..., description="Parent project ID")
    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: str = Field(default="", description="Document content (markdown)")
    template_type: str | None = Field(None, description="Template type to use")
    
    @field_validator("template_type")
    @classmethod
    def validate_template_type(cls, v: str | None) -> str | None:
        """Validate template type is one of the allowed values."""
        if v is None:
            return v
        allowed = [
            DocumentTemplateType.PROBLEM_STATEMENT,
            DocumentTemplateType.PRODUCT_VISION,
            DocumentTemplateType.TECHNICAL_DECISION,
            DocumentTemplateType.SPRINT_RETROSPECTIVE
        ]
        if v not in allowed:
            raise ValueError(f"Template type must be one of: {', '.join(allowed)}")
        return v


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""
    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = None


class DocumentResponse(BaseModel):
    """Schema for document API response."""
    id: str
    project_id: str
    title: str
    content: str
    template_type: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class DocumentList(BaseModel):
    """Schema for listing documents with pagination."""
    documents: list[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 50
