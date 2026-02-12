"""
Project API endpoints.

Provides CRUD operations for projects.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DBSession
from app.schemas.project import ProjectCreate, ProjectList, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: DBSession) -> ProjectResponse:
    """Create a new project."""
    service = ProjectService(db)
    project = await service.create(data)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectList)
async def list_projects(
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ProjectList:
    """List all projects with pagination."""
    service = ProjectService(db)
    return await service.list(page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: DBSession) -> ProjectResponse:
    """Get a project by ID."""
    service = ProjectService(db)
    project = await service.get(project_id)
    return ProjectResponse.model_validate(project)
