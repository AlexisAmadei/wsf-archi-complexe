"""
Project service implementing business logic for projects.

Handles CRUD operations for projects: create, get, list.
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectList, ProjectResponse


class ProjectService:
    """Service for managing projects."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize project service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create(self, data: ProjectCreate) -> Project:
        """
        Create a new project.
        
        Args:
            data: Project creation data
            
        Returns:
            Created project
        """
        project = Project(
            id=f"proj_{uuid.uuid4().hex[:12]}",
            name=data.name,
            description=data.description,
        )
        
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        
        return project
    
    async def get(self, project_id: str) -> Project:
        """
        Get a project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project instance
            
        Raises:
            NotFoundError: If project not found
        """
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"Project with id '{project_id}' not found")
        
        return project
    
    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> ProjectList:
        """
        List projects with pagination.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            ProjectList with projects and pagination info
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Project)
        )
        total = count_result.scalar_one()
        
        # Get paginated projects
        result = await self.db.execute(
            select(Project)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        projects = result.scalars().all()
        
        return ProjectList(
            projects=[ProjectResponse.model_validate(p) for p in projects],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def delete(self, project_id: str) -> None:
        """
        Delete a project.
        
        Args:
            project_id: Project ID
            
        Raises:
            NotFoundError: If project not found
        """
        project = await self.get(project_id)
        await self.db.delete(project)
        await self.db.commit()
