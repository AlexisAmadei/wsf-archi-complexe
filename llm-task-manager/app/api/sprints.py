"""
Sprint API endpoints.

Provides sprint management with lifecycle operations (start, close)
and story assignment (BR-03, BR-04).
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DBSession
from app.schemas.sprint import (
    SprintClosureRequest,
    SprintCreate,
    SprintList,
    SprintResponse,
    SprintStoryAssignment,
)
from app.schemas.story import StoryResponse
from app.services.sprint_service import SprintService

router = APIRouter()


@router.post("", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
async def create_sprint(data: SprintCreate, db: DBSession) -> SprintResponse:
    """Create a new sprint within a project."""
    service = SprintService(db)
    sprint = await service.create(data)
    return SprintResponse.model_validate(sprint)


@router.get("", response_model=SprintList)
async def list_sprints(
    db: DBSession,
    project_id: str | None = Query(None, description="Filter by project ID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> SprintList:
    """List sprints with optional filters and pagination."""
    service = SprintService(db)
    return await service.list(
        project_id=project_id, status=status_filter, page=page, page_size=page_size
    )


@router.get("/{sprint_id}", response_model=SprintResponse)
async def get_sprint(sprint_id: str, db: DBSession) -> SprintResponse:
    """Get a sprint by ID."""
    service = SprintService(db)
    sprint = await service.get(sprint_id)
    return SprintResponse.model_validate(sprint)


@router.post("/{sprint_id}/start", response_model=SprintResponse)
async def start_sprint(sprint_id: str, db: DBSession) -> SprintResponse:
    """
    Start a sprint (planning → active).
    
    Only sprints in 'planning' status can be started.
    """
    service = SprintService(db)
    sprint = await service.start(sprint_id)
    return SprintResponse.model_validate(sprint)


@router.post("/{sprint_id}/close", response_model=SprintResponse)
async def close_sprint(
    sprint_id: str, db: DBSession, data: SprintClosureRequest | None = None
) -> SprintResponse:
    """
    Close a sprint (active → closed).
    
    BR-04: Cannot close if stories are still in progress unless force=True.
    """
    force = data.force if data else False
    service = SprintService(db)
    sprint = await service.close(sprint_id, force=force)
    return SprintResponse.model_validate(sprint)


@router.post("/{sprint_id}/stories", status_code=status.HTTP_201_CREATED)
async def assign_story_to_sprint(
    sprint_id: str, data: SprintStoryAssignment, db: DBSession
) -> dict:
    """
    Assign a story to a sprint.
    
    BR-03: A story can only be assigned to one active sprint at a time.
    """
    service = SprintService(db)
    await service.assign_story(sprint_id, data.story_id)
    return {"message": f"Story '{data.story_id}' assigned to sprint '{sprint_id}'"}


@router.delete("/{sprint_id}/stories/{story_id}", status_code=status.HTTP_200_OK)
async def remove_story_from_sprint(sprint_id: str, story_id: str, db: DBSession) -> dict:
    """Remove a story from a sprint."""
    service = SprintService(db)
    await service.remove_story(sprint_id, story_id)
    return {"message": f"Story '{story_id}' removed from sprint '{sprint_id}'"}


@router.get("/{sprint_id}/stories", response_model=list[StoryResponse])
async def get_sprint_stories(sprint_id: str, db: DBSession) -> list[StoryResponse]:
    """Get all stories assigned to a sprint."""
    service = SprintService(db)
    stories = await service.get_sprint_stories(sprint_id)
    return [StoryResponse.model_validate(s) for s in stories]
