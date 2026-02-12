"""
Comment API endpoints.

Provides polymorphic comment operations for any entity type.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DBSession
from app.schemas.comment import CommentCreate, CommentList, CommentResponse
from app.services.comment_service import CommentService

router = APIRouter()


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(data: CommentCreate, db: DBSession) -> CommentResponse:
    """Add a comment to an entity (epic, story, sprint, or document)."""
    service = CommentService(db)
    comment = await service.add(data)
    return CommentResponse.model_validate(comment)


@router.get("", response_model=CommentList)
async def list_comments(
    db: DBSession,
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> CommentList:
    """
    List comments with optional filters.
    
    When both entity_type and entity_id are provided, returns comments for that specific entity.
    When only entity_type is provided, returns all comments of that type.
    """
    service = CommentService(db)
    if entity_type and entity_id:
        return await service.list_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size,
        )
    return await service.list_all(
        entity_type=entity_type,
        page=page,
        page_size=page_size,
    )
