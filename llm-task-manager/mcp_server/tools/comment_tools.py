"""
MCP Tools for Comment management.

Comments are polymorphic and can be attached to any entity
(epic, story, sprint, document).

Tools:
- add_comment: Add a comment to any entity
- list_comments: List comments for a specific entity
"""

from app.schemas.comment import CommentCreate, CommentResponse
from mcp_server.server import mcp
from mcp_server.shared_services import get_comment_service, serialize_response


@mcp.tool()
async def add_comment(
    entity_type: str,
    entity_id: str,
    content: str,
    author: str,
) -> str:
    """Add a comment to any entity (epic, story, sprint, or document).

    Use this tool when the user wants to:
    - Leave a note on a story or epic
    - Add feedback or discussion to an item
    - Document a decision or observation
    - Mention that a PR is ready or needs review

    Args:
        entity_type: Type of entity - one of: epic, story, sprint, document (required)
        entity_id: The ID of the entity to comment on (required)
        content: Comment text in markdown (required)
        author: Name of the comment author (required)

    Returns:
        JSON with created comment details including its ID

    Example:
        add_comment(
            entity_type="story",
            entity_id="story_abc123",
            content="PR #42 is ready for review",
            author="Alice"
        )
    """
    async with get_comment_service() as service:
        comment = await service.add(
            CommentCreate(
                entity_type=entity_type,
                entity_id=entity_id,
                content=content,
                author=author,
            )
        )
        return serialize_response(CommentResponse.model_validate(comment))


@mcp.tool()
async def list_comments(
    entity_type: str,
    entity_id: str,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List all comments for a specific entity.

    Use this tool when the user wants to:
    - See all comments on a story or epic
    - Review discussion history
    - Check feedback on an item

    Args:
        entity_type: Type of entity - one of: epic, story, sprint, document (required)
        entity_id: The ID of the entity (required)
        page: Page number, starting from 1 (default: 1)
        page_size: Number of comments per page (default: 50, max: 100)

    Returns:
        JSON with list of comments and pagination info
    """
    async with get_comment_service() as service:
        result = await service.list_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size,
        )
        return serialize_response(result)
