"""
Comment service implementing business logic for comments.

Handles polymorphic comments that can be attached to any entity
(epic, story, sprint, document).
"""

import uuid
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.comment import Comment, CommentEntityType
from app.schemas.comment import CommentCreate, CommentList, CommentResponse


class CommentService:
    """Service for managing polymorphic comments."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize comment service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def add(self, data: CommentCreate) -> Comment:
        """
        Add a comment to an entity.
        
        Args:
            data: Comment creation data
            
        Returns:
            Created comment
            
        Note:
            Does not validate if the entity exists. This allows for flexible
            comment systems where the entity might be in a different service.
        """
        comment = Comment(
            id=f"comment_{uuid.uuid4().hex[:12]}",
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            content=data.content,
            author=data.author,
        )
        
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        
        return comment
    
    async def get(self, comment_id: str) -> Comment:
        """
        Get a comment by ID.
        
        Args:
            comment_id: Comment ID
            
        Returns:
            Comment instance
            
        Raises:
            NotFoundError: If comment not found
        """
        result = await self.db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise NotFoundError(f"Comment with id '{comment_id}' not found")
        
        return comment
    
    async def list_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> CommentList:
        """
        List all comments for a specific entity.
        
        Args:
            entity_type: Type of entity (epic, story, sprint, document)
            entity_id: ID of the entity
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            CommentList with comments and pagination info
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build query
        query = select(Comment).where(
            and_(
                Comment.entity_type == entity_type,
                Comment.entity_id == entity_id,
            )
        )
        
        # Get total count
        count_query = select(func.count()).select_from(Comment).where(
            and_(
                Comment.entity_type == entity_type,
                Comment.entity_id == entity_id,
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated comments (ordered by creation time, newest first)
        query = query.order_by(Comment.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        comments = result.scalars().all()
        
        return CommentList(
            comments=[CommentResponse.model_validate(c) for c in comments],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def list_all(
        self,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> CommentList:
        """
        List all comments with optional entity type filter.
        
        Args:
            entity_type: Optional filter by entity type
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            CommentList with comments and pagination info
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build query
        query = select(Comment)
        count_query = select(func.count()).select_from(Comment)
        
        if entity_type:
            query = query.where(Comment.entity_type == entity_type)
            count_query = count_query.where(Comment.entity_type == entity_type)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated comments
        query = query.order_by(Comment.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        comments = result.scalars().all()
        
        return CommentList(
            comments=[CommentResponse.model_validate(c) for c in comments],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def delete(self, comment_id: str) -> None:
        """
        Delete a comment.
        
        Args:
            comment_id: Comment ID
            
        Raises:
            NotFoundError: If comment not found
        """
        comment = await self.get(comment_id)
        await self.db.delete(comment)
        await self.db.commit()
