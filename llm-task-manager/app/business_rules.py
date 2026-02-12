"""
Business Rules Engine.

Implements the 4 core business rules:
- BR-01: Story points must be Fibonacci values
- BR-02: Story status transitions follow a state machine
- BR-03: A story can only be in one active sprint at a time
- BR-04: Sprint can only be closed if no stories are in progress
"""

from app.exceptions import BusinessRuleViolation
from app.models.sprint import SprintStatus
from app.models.story import Story, StoryStatus


# BR-01: Fibonacci values for story points
FIBONACCI_VALUES = [None, 1, 2, 3, 5, 8, 13, 21]


# BR-02: State machine for story status transitions
STORY_TRANSITIONS = {
    StoryStatus.BACKLOG: [StoryStatus.TODO],
    StoryStatus.TODO: [StoryStatus.IN_PROGRESS, StoryStatus.BACKLOG],
    StoryStatus.IN_PROGRESS: [StoryStatus.IN_REVIEW, StoryStatus.TODO],
    StoryStatus.IN_REVIEW: [StoryStatus.DONE, StoryStatus.IN_PROGRESS],
    StoryStatus.DONE: [],  # Terminal state
}


class BusinessRulesEngine:
    """Engine for validating business rules."""
    
    @staticmethod
    def validate_story_points(points: int | None) -> bool:
        """
        BR-01: Validate story points are Fibonacci values or NULL.
        
        Args:
            points: Story points value
            
        Returns:
            bool: True if valid
            
        Raises:
            BusinessRuleViolation: If points are not Fibonacci values
        """
        if points not in FIBONACCI_VALUES:
            valid_points = [str(p) for p in FIBONACCI_VALUES if p is not None]
            raise BusinessRuleViolation(
                f"Story points must be one of: {', '.join(valid_points)} or NULL. Got: {points}"
            )
        return True
    
    @staticmethod
    def can_transition(from_status: str, to_status: str) -> bool:
        """
        BR-02: Check if story status transition is valid.
        
        Args:
            from_status: Current status
            to_status: Target status
            
        Returns:
            bool: True if transition is allowed
        """
        allowed_transitions = STORY_TRANSITIONS.get(from_status, [])
        return to_status in allowed_transitions
    
    @staticmethod
    def validate_transition(from_status: str, to_status: str) -> bool:
        """
        BR-02: Validate story status transition.
        
        Args:
            from_status: Current status
            to_status: Target status
            
        Returns:
            bool: True if valid
            
        Raises:
            BusinessRuleViolation: If transition is not allowed
        """
        if not BusinessRulesEngine.can_transition(from_status, to_status):
            allowed = STORY_TRANSITIONS.get(from_status, [])
            allowed_str = ', '.join(allowed) if allowed else 'none (terminal state)'
            raise BusinessRuleViolation(
                f"Cannot transition from '{from_status}' to '{to_status}'. "
                f"Allowed transitions: {allowed_str}"
            )
        return True
    
    @staticmethod
    def validate_unique_active_sprint(story_id: str, active_sprint_count: int) -> bool:
        """
        BR-03: Validate that a story is not already in another active sprint.
        
        This is enforced at the database level with a partial unique index,
        but we also validate it in the application layer.
        
        Args:
            story_id: ID of the story
            active_sprint_count: Number of active sprints the story is currently in
            
        Returns:
            bool: True if valid
            
        Raises:
            BusinessRuleViolation: If story is already in an active sprint
        """
        if active_sprint_count > 0:
            raise BusinessRuleViolation(
                f"Story {story_id} is already assigned to an active sprint. "
                "A story can only be in one active sprint at a time."
            )
        return True
    
    @staticmethod
    def can_close_sprint(stories: list[Story]) -> tuple[bool, str]:
        """
        BR-04: Check if a sprint can be closed.
        
        A sprint can only be closed if no stories are in progress or in review.
        
        Args:
            stories: List of stories in the sprint
            
        Returns:
            tuple[bool, str]: (can_close, reason)
        """
        in_progress_statuses = [StoryStatus.IN_PROGRESS, StoryStatus.IN_REVIEW]
        in_progress_stories = [
            s for s in stories 
            if s.status in in_progress_statuses
        ]
        
        if in_progress_stories:
            story_list = ", ".join([f"{s.id} ({s.status})" for s in in_progress_stories])
            return False, f"{len(in_progress_stories)} stories still in progress: {story_list}"
        
        return True, ""
    
    @staticmethod
    def validate_sprint_closure(stories: list[Story], force: bool = False) -> bool:
        """
        BR-04: Validate sprint can be closed.
        
        Args:
            stories: List of stories in the sprint
            force: If True, allow closing even with in-progress stories
            
        Returns:
            bool: True if valid
            
        Raises:
            BusinessRuleViolation: If sprint cannot be closed
        """
        if force:
            return True
        
        can_close, reason = BusinessRulesEngine.can_close_sprint(stories)
        if not can_close:
            raise BusinessRuleViolation(
                f"Cannot close sprint: {reason}. "
                "Move stories to 'todo' or 'done' before closing, or use force=true."
            )
        return True


# Export singleton instance
rules_engine = BusinessRulesEngine()
