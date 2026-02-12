"""
Epic API endpoints.

Provides CRUD operations, search and filtering for epics.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DBSession
from app.schemas.epic import EpicCreate, EpicList, EpicResponse, EpicUpdate
from app.services.epic_service import EpicService

router = APIRouter()


@router.post("", response_model=EpicResponse, status_code=status.HTTP_201_CREATED)
async def create_epic(data: EpicCreate, db: DBSession) -> EpicResponse:
    """Create a new epic within a project."""
    service = EpicService(db)
    epic = await service.create(data)
    return EpicResponse.model_validate(epic)


@router.get("/search", response_model=EpicList)
async def search_epics(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search keyword"),
    project_id: str | None = Query(None, description="Filter by project ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> EpicList:
    """Search epics by keyword in title and description."""
    service = EpicService(db)
    return await service.search(keyword=q, project_id=project_id, page=page, page_size=page_size)


@router.get("", response_model=EpicList)
async def list_epics(
    db: DBSession,
    project_id: str | None = Query(None, description="Filter by project ID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> EpicList:
    """List epics with optional filters and pagination."""
    service = EpicService(db)
    return await service.list(
        project_id=project_id, status=status_filter, page=page, page_size=page_size
    )


@router.get("/{epic_id}", response_model=EpicResponse)
async def get_epic(epic_id: str, db: DBSession) -> EpicResponse:
    """Get an epic by ID."""
    service = EpicService(db)
    epic = await service.get(epic_id)
    return EpicResponse.model_validate(epic)


@router.patch("/{epic_id}", response_model=EpicResponse)
async def update_epic(epic_id: str, data: EpicUpdate, db: DBSession) -> EpicResponse:
    """Update an epic (partial update)."""
    service = EpicService(db)
    epic = await service.update(epic_id, data)
    return EpicResponse.model_validate(epic)
