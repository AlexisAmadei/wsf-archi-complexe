"""
Story service implementing business logic for stories.

Handles CRUD operations and implements BR-01 (Fibonacci points) 
and BR-02 (status transitions).
"""

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules import BusinessRulesEngine
from app.exceptions import NotFoundError
from app.models.epic import Epic
from app.models.story import Story, StoryStatus
from app.schemas.story import StoryCreate, StoryList, StoryResponse, StoryUpdate


class StoryService:
    """Service for managing stories with business rules enforcement."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize story service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.rules = BusinessRulesEngine()
    
    async def create(self, data: StoryCreate) -> Story:
        """
        Create a new story.
        
        Validates BR-01 (Fibonacci story points).
        
        Args:
            data: Story creation data
            
        Returns:
            Created story
            
        Raises:
            NotFoundError: If parent epic not found
            BusinessRuleViolation: If story points invalid
        """
        # Verify epic exists
        epic_result = await self.db.execute(
            select(Epic).where(Epic.id == data.epic_id)
        )
        if not epic_result.scalar_one_or_none():
            raise NotFoundError(f"Epic with id '{data.epic_id}' not found")
        
        # BR-01: Validate story points
        self.rules.validate_story_points(data.story_points)
        
        story = Story(
            id=f"story_{uuid.uuid4().hex[:12]}",
            epic_id=data.epic_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            story_points=data.story_points,
            assignee=data.assignee,
            status=StoryStatus.BACKLOG,
        )
        
        self.db.add(story)
        await self.db.commit()
        await self.db.refresh(story)
        
        return story
    
    async def get(self, story_id: str) -> Story:
        """
        Get a story by ID.
        
        Args:
            story_id: Story ID
            
        Returns:
            Story instance
            
        Raises:
            NotFoundError: If story not found
        """
        result = await self.db.execute(
            select(Story).where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()
        
        if not story:
            raise NotFoundError(f"Story with id '{story_id}' not found")
        
        return story
    
    async def update(self, story_id: str, data: StoryUpdate) -> Story:
        """
        Update a story.
        
        Validates BR-01 (Fibonacci story points) if story_points are updated.
        
        Args:
            story_id: Story ID
            data: Update data (only non-None fields will be updated)
            
        Returns:
            Updated story
            
        Raises:
            NotFoundError: If story not found
            BusinessRuleViolation: If story points invalid
        """
        story = await self.get(story_id)
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        
        # BR-01: Validate story points if being updated
        if "story_points" in update_data:
            self.rules.validate_story_points(update_data["story_points"])
        
        for field, value in update_data.items():
            setattr(story, field, value)
        
        await self.db.commit()
        await self.db.refresh(story)
        
        return story
    
    async def transition_status(self, story_id: str, new_status: str) -> Story:
        """
        Transition a story to a new status.
        
        Implements BR-02 (status transition state machine).
        
        Args:
            story_id: Story ID
            new_status: Target status
            
        Returns:
            Updated story
            
        Raises:
            NotFoundError: If story not found
            BusinessRuleViolation: If transition is not allowed
        """
        story = await self.get(story_id)
        
        # BR-02: Validate status transition
        self.rules.validate_transition(story.status, new_status)
        
        story.status = new_status
        await self.db.commit()
        await self.db.refresh(story)
        
        return story
    
    async def list(
        self,
        epic_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        sprint_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> StoryList:
        """
        List stories with optional filters and pagination.
        
        Args:
            epic_id: Filter by epic ID
            status: Filter by status
            priority: Filter by priority
            assignee: Filter by assignee
            sprint_id: Filter by sprint ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            StoryList with stories and pagination info
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build query with filters
        query = select(Story)
        count_query = select(func.count()).select_from(Story)
        
        if epic_id:
            query = query.where(Story.epic_id == epic_id)
            count_query = count_query.where(Story.epic_id == epic_id)
        
        if status:
            query = query.where(Story.status == status)
            count_query = count_query.where(Story.status == status)
        
        if priority:
            query = query.where(Story.priority == priority)
            count_query = count_query.where(Story.priority == priority)
        
        if assignee:
            query = query.where(Story.assignee == assignee)
            count_query = count_query.where(Story.assignee == assignee)
        
        if sprint_id:
            # Join with story_sprint table for sprint filtering
            from app.models.sprint import story_sprint
            query = query.join(story_sprint).where(story_sprint.c.sprint_id == sprint_id)
            count_query = count_query.join(story_sprint).where(story_sprint.c.sprint_id == sprint_id)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated stories
        query = query.order_by(Story.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        stories = result.scalars().all()
        
        return StoryList(
            stories=[StoryResponse.model_validate(s) for s in stories],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def search(
        self,
        keyword: str,
        epic_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> StoryList:
        """
        Search stories by keyword in title and description.
        
        Args:
            keyword: Search keyword
            epic_id: Optional filter by epic
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            StoryList with matching stories
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build search query
        search_pattern = f"%{keyword}%"
        query = select(Story).where(
            or_(
                Story.title.ilike(search_pattern),
                Story.description.ilike(search_pattern),
            )
        )
        
        count_query = select(func.count()).select_from(Story).where(
            or_(
                Story.title.ilike(search_pattern),
                Story.description.ilike(search_pattern),
            )
        )
        
        if epic_id:
            query = query.where(Story.epic_id == epic_id)
            count_query = count_query.where(Story.epic_id == epic_id)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.order_by(Story.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        stories = result.scalars().all()
        
        return StoryList(
            stories=[StoryResponse.model_validate(s) for s in stories],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def filter_by_status(
        self,
        status: str,
        epic_id: Optional[str] = None,
    ) -> list[Story]:
        """
        Get all stories with a specific status.
        
        Args:
            status: Story status to filter by
            epic_id: Optional filter by epic
            
        Returns:
            List of stories with matching status
        """
        query = select(Story).where(Story.status == status)
        
        if epic_id:
            query = query.where(Story.epic_id == epic_id)
        
        query = query.order_by(Story.created_at.desc())
        result = await self.db.execute(query)
        
        return list(result.scalars().all())
    
    async def delete(self, story_id: str) -> None:
        """
        Delete a story.
        
        Args:
            story_id: Story ID
            
        Raises:
            NotFoundError: If story not found
        """
        story = await self.get(story_id)
        await self.db.delete(story)
        await self.db.commit()
