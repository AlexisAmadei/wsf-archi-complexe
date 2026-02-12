"""
Document service implementing business logic for documents.

Handles document management with template support for:
- Problem Statement
- Product Vision
- Technical Decision Record
- Sprint Retrospective
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.document import Document, DocumentTemplateType
from app.models.project import Project
from app.schemas.document import DocumentCreate, DocumentList, DocumentResponse, DocumentUpdate


# Document templates
DOCUMENT_TEMPLATES = {
    DocumentTemplateType.PROBLEM_STATEMENT: """# Problem Statement

## Context
Describe the current situation and background.

## Problem
What is the specific problem we're trying to solve?

## Impact
- Who is affected by this problem?
- What is the business impact?
- What happens if we don't solve it?

## Success Criteria
How will we know when this problem is solved?

## Constraints
What are the limitations or constraints we need to consider?
""",
    
    DocumentTemplateType.PRODUCT_VISION: """# Product Vision

## Vision Statement
A clear, inspiring statement of what we want to achieve.

## Target Audience
Who are we building this for?

## Key Benefits
- Benefit 1
- Benefit 2
- Benefit 3

## Differentiators
What makes this unique or better than alternatives?

## Success Metrics
How will we measure success?

## Timeline
High-level timeline and milestones.
""",
    
    DocumentTemplateType.TECHNICAL_DECISION: """# Technical Decision Record

## Status
[Proposed | Accepted | Rejected | Deprecated | Superseded]

## Context
What is the issue we're trying to solve?

## Decision
What is the decision we've made?

## Alternatives Considered
1. Alternative 1
   - Pros:
   - Cons:

2. Alternative 2
   - Pros:
   - Cons:

## Consequences
### Positive
- Consequence 1

### Negative
- Consequence 1

### Neutral
- Consequence 1

## Implementation Notes
Key considerations for implementation.
""",
    
    DocumentTemplateType.SPRINT_RETROSPECTIVE: """# Sprint Retrospective

## Sprint Information
- Sprint: [Name]
- Date: [Date]
- Participants: [Names]

## What Went Well 🎉
1. 
2. 
3. 

## What Could Be Improved 🔧
1. 
2. 
3. 

## Action Items
1. [ ] Action item 1 - Owner: [Name]
2. [ ] Action item 2 - Owner: [Name]
3. [ ] Action item 3 - Owner: [Name]

## Metrics
- Velocity: [X story points]
- Completed Stories: [X/Y]
- Team Satisfaction: [1-10]

## Notes
Additional observations and learnings.
""",
}


class DocumentService:
    """Service for managing documents with template support."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize document service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create(self, data: DocumentCreate) -> Document:
        """
        Create a new document, optionally from a template.
        
        Args:
            data: Document creation data
            
        Returns:
            Created document
            
        Raises:
            NotFoundError: If parent project not found
        """
        # Verify project exists
        project_result = await self.db.execute(
            select(Project).where(Project.id == data.project_id)
        )
        if not project_result.scalar_one_or_none():
            raise NotFoundError(f"Project with id '{data.project_id}' not found")
        
        # Load template content if specified and content is empty
        content = data.content
        if data.template_type and not content:
            content = self.load_template(data.template_type)
        
        document = Document(
            id=f"doc_{uuid.uuid4().hex[:12]}",
            project_id=data.project_id,
            title=data.title,
            content=content,
            template_type=data.template_type,
        )
        
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
        return document
    
    async def get(self, document_id: str) -> Document:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document instance
            
        Raises:
            NotFoundError: If document not found
        """
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise NotFoundError(f"Document with id '{document_id}' not found")
        
        return document
    
    async def update(self, document_id: str, data: DocumentUpdate) -> Document:
        """
        Update a document.
        
        Args:
            document_id: Document ID
            data: Update data (only non-None fields will be updated)
            
        Returns:
            Updated document
            
        Raises:
            NotFoundError: If document not found
        """
        document = await self.get(document_id)
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(document, field, value)
        
        await self.db.commit()
        await self.db.refresh(document)
        
        return document
    
    async def list(
        self,
        project_id: Optional[str] = None,
        template_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DocumentList:
        """
        List documents with optional filters and pagination.
        
        Args:
            project_id: Filter by project ID
            template_type: Filter by template type
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            DocumentList with documents and pagination info
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build query with filters
        query = select(Document)
        count_query = select(func.count()).select_from(Document)
        
        if project_id:
            query = query.where(Document.project_id == project_id)
            count_query = count_query.where(Document.project_id == project_id)
        
        if template_type:
            query = query.where(Document.template_type == template_type)
            count_query = count_query.where(Document.template_type == template_type)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated documents
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        documents = result.scalars().all()
        
        return DocumentList(
            documents=[DocumentResponse.model_validate(d) for d in documents],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def search(
        self,
        keyword: str,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DocumentList:
        """
        Search documents by keyword in title and content.
        
        Args:
            keyword: Search keyword
            project_id: Optional filter by project
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            DocumentList with matching documents
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build search query
        search_pattern = f"%{keyword}%"
        query = select(Document).where(
            or_(
                Document.title.ilike(search_pattern),
                Document.content.ilike(search_pattern),
            )
        )
        
        count_query = select(func.count()).select_from(Document).where(
            or_(
                Document.title.ilike(search_pattern),
                Document.content.ilike(search_pattern),
            )
        )
        
        if project_id:
            query = query.where(Document.project_id == project_id)
            count_query = count_query.where(Document.project_id == project_id)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        documents = result.scalars().all()
        
        return DocumentList(
            documents=[DocumentResponse.model_validate(d) for d in documents],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    def load_template(self, template_type: str) -> str:
        """
        Load a document template by type.
        
        Args:
            template_type: Type of template to load
            
        Returns:
            Template content as markdown string
            
        Raises:
            ValueError: If template type is unknown
        """
        template = DOCUMENT_TEMPLATES.get(template_type)
        if not template:
            raise ValueError(
                f"Unknown template type '{template_type}'. "
                f"Available templates: {', '.join(DOCUMENT_TEMPLATES.keys())}"
            )
        return template
    
    def list_templates(self) -> dict[str, str]:
        """
        Get all available document templates.
        
        Returns:
            Dictionary mapping template types to their names
        """
        return {
            DocumentTemplateType.PROBLEM_STATEMENT: "Problem Statement",
            DocumentTemplateType.PRODUCT_VISION: "Product Vision",
            DocumentTemplateType.TECHNICAL_DECISION: "Technical Decision Record",
            DocumentTemplateType.SPRINT_RETROSPECTIVE: "Sprint Retrospective",
        }
    
    async def delete(self, document_id: str) -> None:
        """
        Delete a document.
        
        Args:
            document_id: Document ID
            
        Raises:
            NotFoundError: If document not found
        """
        document = await self.get(document_id)
        await self.db.delete(document)
        await self.db.commit()
