"""
Story API endpoints.

Provides CRUD operations, status transitions (BR-02), search and filtering.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DBSession
from app.schemas.story import (
    StoryCreate,
    StoryList,
    StoryResponse,
    StoryStatusTransition,
    StoryUpdate,
)
from app.services.story_service import StoryService

router = APIRouter()


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(data: StoryCreate, db: DBSession) -> StoryResponse:
    """Create a new story within an epic."""
    service = StoryService(db)
    story = await service.create(data)
    return StoryResponse.model_validate(story)


@router.get("/search", response_model=StoryList)
async def search_stories(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search keyword"),
    epic_id: str | None = Query(None, description="Filter by epic ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> StoryList:
    """Search stories by keyword in title and description."""
    service = StoryService(db)
    return await service.search(keyword=q, epic_id=epic_id, page=page, page_size=page_size)


@router.get("", response_model=StoryList)
async def list_stories(
    db: DBSession,
    epic_id: str | None = Query(None, description="Filter by epic ID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    assignee: str | None = Query(None, description="Filter by assignee"),
    sprint_id: str | None = Query(None, description="Filter by sprint ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> StoryList:
    """List stories with optional filters and pagination."""
    service = StoryService(db)
    return await service.list(
        epic_id=epic_id,
        status=status_filter,
        priority=priority,
        assignee=assignee,
        sprint_id=sprint_id,
        page=page,
        page_size=page_size,
    )


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str, db: DBSession) -> StoryResponse:
    """Get a story by ID."""
    service = StoryService(db)
    story = await service.get(story_id)
    return StoryResponse.model_validate(story)


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(story_id: str, data: StoryUpdate, db: DBSession) -> StoryResponse:
    """Update a story (partial update)."""
    service = StoryService(db)
    story = await service.update(story_id, data)
    return StoryResponse.model_validate(story)


@router.post("/{story_id}/transition", response_model=StoryResponse)
async def transition_story_status(
    story_id: str, data: StoryStatusTransition, db: DBSession
) -> StoryResponse:
    """
    Transition a story to a new status.
    
    Follows BR-02 state machine:
    - backlog → todo
    - todo → in_progress | backlog  
    - in_progress → in_review | todo
    - in_review → done | in_progress
    - done → (terminal)
    """
    service = StoryService(db)
    story = await service.transition_status(story_id, data.new_status)
    return StoryResponse.model_validate(story)
