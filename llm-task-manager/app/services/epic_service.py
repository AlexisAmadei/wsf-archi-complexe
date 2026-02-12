"""
Epic service implementing business logic for epics.

Handles CRUD operations: create, get, update, list, search, filter by status.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.epic import Epic, EpicStatus
from app.models.project import Project
from app.schemas.epic import EpicCreate, EpicList, EpicResponse, EpicUpdate


class EpicService:
    """Service for managing epics."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize epic service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create(self, data: EpicCreate) -> Epic:
        """
        Create a new epic.
        
        Args:
            data: Epic creation data
            
        Returns:
            Created epic
            
        Raises:
            NotFoundError: If parent project not found
        """
        # Verify project exists
        project_result = await self.db.execute(
            select(Project).where(Project.id == data.project_id)
        )
        if not project_result.scalar_one_or_none():
            raise NotFoundError(f"Project with id '{data.project_id}' not found")
        
        epic = Epic(
            id=f"epic_{uuid.uuid4().hex[:12]}",
            project_id=data.project_id,
            title=data.title,
            description=data.description,
            status=data.status,
        )
        
        self.db.add(epic)
        await self.db.commit()
        await self.db.refresh(epic)
        
        return epic
    
    async def get(self, epic_id: str) -> Epic:
        """
        Get an epic by ID.
        
        Args:
            epic_id: Epic ID
            
        Returns:
            Epic instance
            
        Raises:
            NotFoundError: If epic not found
        """
        result = await self.db.execute(
            select(Epic).where(Epic.id == epic_id)
        )
        epic = result.scalar_one_or_none()
        
        if not epic:
            raise NotFoundError(f"Epic with id '{epic_id}' not found")
        
        return epic
    
    async def update(self, epic_id: str, data: EpicUpdate) -> Epic:
        """
        Update an epic.
        
        Args:
            epic_id: Epic ID
            data: Update data (only non-None fields will be updated)
            
        Returns:
            Updated epic
            
        Raises:
            NotFoundError: If epic not found
        """
        epic = await self.get(epic_id)
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(epic, field, value)
        
        await self.db.commit()
        await self.db.refresh(epic)
        
        return epic
    
    async def list(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> EpicList:
        """
        List epics with optional filters and pagination.
        
        Args:
            project_id: Filter by project ID
            status: Filter by status
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            EpicList with epics and pagination info
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build query with filters
        query = select(Epic)
        
        if project_id:
            query = query.where(Epic.project_id == project_id)
        
        if status:
            query = query.where(Epic.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(Epic)
        if project_id:
            count_query = count_query.where(Epic.project_id == project_id)
        if status:
            count_query = count_query.where(Epic.status == status)
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated epics
        query = query.order_by(Epic.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        epics = result.scalars().all()
        
        return EpicList(
            epics=[EpicResponse.model_validate(e) for e in epics],
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
    ) -> EpicList:
        """
        Search epics by keyword in title and description.
        
        Args:
            keyword: Search keyword
            project_id: Optional filter by project
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            EpicList with matching epics
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build search query
        search_pattern = f"%{keyword}%"
        query = select(Epic).where(
            or_(
                Epic.title.ilike(search_pattern),
                Epic.description.ilike(search_pattern),
            )
        )
        
        if project_id:
            query = query.where(Epic.project_id == project_id)
        
        # Get total count
        count_query = select(func.count()).select_from(Epic).where(
            or_(
                Epic.title.ilike(search_pattern),
                Epic.description.ilike(search_pattern),
            )
        )
        if project_id:
            count_query = count_query.where(Epic.project_id == project_id)
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.order_by(Epic.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        epics = result.scalars().all()
        
        return EpicList(
            epics=[EpicResponse.model_validate(e) for e in epics],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def filter_by_status(
        self,
        status: str,
        project_id: Optional[str] = None,
    ) -> list[Epic]:
        """
        Get all epics with a specific status.
        
        Args:
            status: Epic status to filter by
            project_id: Optional filter by project
            
        Returns:
            List of epics with matching status
        """
        query = select(Epic).where(Epic.status == status)
        
        if project_id:
            query = query.where(Epic.project_id == project_id)
        
        query = query.order_by(Epic.created_at.desc())
        result = await self.db.execute(query)
        
        return list(result.scalars().all())
    
    async def delete(self, epic_id: str) -> None:
        """
        Delete an epic.
        
        Args:
            epic_id: Epic ID
            
        Raises:
            NotFoundError: If epic not found
        """
        epic = await self.get(epic_id)
        await self.db.delete(epic)
        await self.db.commit()
