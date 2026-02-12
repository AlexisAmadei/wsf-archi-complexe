"""
Sprint service implementing business logic for sprints.

Handles sprint management and implements:
- BR-03: A story can only be in one active sprint
- BR-04: Sprint closure rules (no in-progress stories)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules import BusinessRulesEngine
from app.exceptions import BusinessRuleViolation, NotFoundError
from app.models.project import Project
from app.models.sprint import Sprint, SprintStatus, story_sprint
from app.models.story import Story
from app.schemas.sprint import SprintCreate, SprintList, SprintResponse, SprintUpdate


class SprintService:
    """Service for managing sprints with business rules enforcement."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize sprint service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.rules = BusinessRulesEngine()
    
    async def create(self, data: SprintCreate) -> Sprint:
        """
        Create a new sprint.
        
        Args:
            data: Sprint creation data
            
        Returns:
            Created sprint (status: planning)
            
        Raises:
            NotFoundError: If parent project not found
        """
        # Verify project exists
        project_result = await self.db.execute(
            select(Project).where(Project.id == data.project_id)
        )
        if not project_result.scalar_one_or_none():
            raise NotFoundError(f"Project with id '{data.project_id}' not found")
        
        sprint = Sprint(
            id=f"sprint_{uuid.uuid4().hex[:12]}",
            project_id=data.project_id,
            name=data.name,
            goal=data.goal,
            status=SprintStatus.PLANNING,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        
        self.db.add(sprint)
        await self.db.commit()
        await self.db.refresh(sprint)
        
        return sprint
    
    async def get(self, sprint_id: str) -> Sprint:
        """
        Get a sprint by ID.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            Sprint instance
            
        Raises:
            NotFoundError: If sprint not found
        """
        result = await self.db.execute(
            select(Sprint).where(Sprint.id == sprint_id)
        )
        sprint = result.scalar_one_or_none()
        
        if not sprint:
            raise NotFoundError(f"Sprint with id '{sprint_id}' not found")
        
        return sprint
    
    async def update(self, sprint_id: str, data: SprintUpdate) -> Sprint:
        """
        Update a sprint.
        
        Args:
            sprint_id: Sprint ID
            data: Update data (only non-None fields will be updated)
            
        Returns:
            Updated sprint
            
        Raises:
            NotFoundError: If sprint not found
        """
        sprint = await self.get(sprint_id)
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sprint, field, value)
        
        await self.db.commit()
        await self.db.refresh(sprint)
        
        return sprint
    
    async def start(self, sprint_id: str) -> Sprint:
        """
        Start a sprint (transition from planning to active).
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            Updated sprint with active status
            
        Raises:
            NotFoundError: If sprint not found
            BusinessRuleViolation: If sprint is not in planning status
        """
        sprint = await self.get(sprint_id)
        
        if sprint.status != SprintStatus.PLANNING:
            raise BusinessRuleViolation(
                f"Cannot start sprint with status '{sprint.status}'. "
                "Only sprints in 'planning' status can be started."
            )
        
        sprint.status = SprintStatus.ACTIVE
        if not sprint.start_date:
            sprint.start_date = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(sprint)
        
        return sprint
    
    async def close(self, sprint_id: str, force: bool = False) -> Sprint:
        """
        Close a sprint (transition from active to closed).
        
        Implements BR-04: Sprint can only be closed if no stories are in progress,
        unless force=True.
        
        Args:
            sprint_id: Sprint ID
            force: If True, allow closing with in-progress stories
            
        Returns:
            Updated sprint with closed status
            
        Raises:
            NotFoundError: If sprint not found
            BusinessRuleViolation: If sprint cannot be closed
        """
        sprint = await self.get(sprint_id)
        
        if sprint.status != SprintStatus.ACTIVE:
            raise BusinessRuleViolation(
                f"Cannot close sprint with status '{sprint.status}'. "
                "Only sprints in 'active' status can be closed."
            )
        
        # Get all stories in this sprint
        stories = await self._get_sprint_stories(sprint_id)
        
        # BR-04: Validate sprint can be closed
        self.rules.validate_sprint_closure(stories, force=force)
        
        sprint.status = SprintStatus.CLOSED
        if not sprint.end_date:
            sprint.end_date = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(sprint)
        
        return sprint
    
    async def assign_story(self, sprint_id: str, story_id: str) -> None:
        """
        Assign a story to a sprint.
        
        Implements BR-03: A story can only be in one active sprint at a time.
        
        Args:
            sprint_id: Sprint ID
            story_id: Story ID to assign
            
        Raises:
            NotFoundError: If sprint or story not found
            BusinessRuleViolation: If story is already in an active sprint
        """
        # Verify sprint and story exist
        sprint = await self.get(sprint_id)
        
        story_result = await self.db.execute(
            select(Story).where(Story.id == story_id)
        )
        story = story_result.scalar_one_or_none()
        if not story:
            raise NotFoundError(f"Story with id '{story_id}' not found")
        
        # BR-03: Check if story is already in an active sprint
        if sprint.status == SprintStatus.ACTIVE:
            active_sprint_count = await self._count_active_sprints_for_story(story_id)
            self.rules.validate_unique_active_sprint(story_id, active_sprint_count)
        
        # Check if already assigned
        existing = await self.db.execute(
            select(story_sprint).where(
                and_(
                    story_sprint.c.story_id == story_id,
                    story_sprint.c.sprint_id == sprint_id,
                )
            )
        )
        if existing.first():
            # Already assigned, silently return
            return
        
        # Insert into association table
        await self.db.execute(
            story_sprint.insert().values(
                story_id=story_id,
                sprint_id=sprint_id,
                sprint_status=sprint.status,
                assigned_at=datetime.utcnow(),
            )
        )
        await self.db.commit()
    
    async def remove_story(self, sprint_id: str, story_id: str) -> None:
        """
        Remove a story from a sprint.
        
        Args:
            sprint_id: Sprint ID
            story_id: Story ID to remove
            
        Raises:
            NotFoundError: If sprint or story not found, or story not in sprint
        """
        # Verify sprint exists
        await self.get(sprint_id)
        
        # Check if story is in sprint
        existing = await self.db.execute(
            select(story_sprint).where(
                and_(
                    story_sprint.c.story_id == story_id,
                    story_sprint.c.sprint_id == sprint_id,
                )
            )
        )
        if not existing.first():
            raise NotFoundError(
                f"Story '{story_id}' is not assigned to sprint '{sprint_id}'"
            )
        
        # Remove from association table
        await self.db.execute(
            story_sprint.delete().where(
                and_(
                    story_sprint.c.story_id == story_id,
                    story_sprint.c.sprint_id == sprint_id,
                )
            )
        )
        await self.db.commit()
    
    async def list(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SprintList:
        """
        List sprints with optional filters and pagination.
        
        Args:
            project_id: Filter by project ID
            status: Filter by status
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            SprintList with sprints and pagination info
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        
        # Build query with filters
        query = select(Sprint)
        count_query = select(func.count()).select_from(Sprint)
        
        if project_id:
            query = query.where(Sprint.project_id == project_id)
            count_query = count_query.where(Sprint.project_id == project_id)
        
        if status:
            query = query.where(Sprint.status == status)
            count_query = count_query.where(Sprint.status == status)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated sprints
        query = query.order_by(Sprint.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        sprints = result.scalars().all()
        
        return SprintList(
            sprints=[SprintResponse.model_validate(s) for s in sprints],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_sprint_stories(self, sprint_id: str) -> list[Story]:
        """
        Get all stories in a sprint.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            List of stories in the sprint
        """
        await self.get(sprint_id)  # Verify sprint exists
        return await self._get_sprint_stories(sprint_id)
    
    async def _get_sprint_stories(self, sprint_id: str) -> list[Story]:
        """
        Internal method to get sprint stories without validation.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            List of stories
        """
        result = await self.db.execute(
            select(Story)
            .join(story_sprint)
            .where(story_sprint.c.sprint_id == sprint_id)
        )
        return list(result.scalars().all())
    
    async def _count_active_sprints_for_story(self, story_id: str) -> int:
        """
        Count how many active sprints a story is currently in.
        
        Args:
            story_id: Story ID
            
        Returns:
            Count of active sprints
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(story_sprint)
            .join(Sprint, Sprint.id == story_sprint.c.sprint_id)
            .where(
                and_(
                    story_sprint.c.story_id == story_id,
                    Sprint.status == SprintStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one()
    
    async def delete(self, sprint_id: str) -> None:
        """
        Delete a sprint.
        
        Args:
            sprint_id: Sprint ID
            
        Raises:
            NotFoundError: If sprint not found
        """
        sprint = await self.get(sprint_id)
        await self.db.delete(sprint)
        await self.db.commit()
