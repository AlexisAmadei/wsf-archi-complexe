"""
Shared services factory for MCP server.

Provides database session management and service instantiation
independent from FastAPI. The MCP server accesses the same database
and reuses the same business logic services as the REST API.
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.services.comment_service import CommentService
from app.services.document_service import DocumentService
from app.services.epic_service import EpicService
from app.services.project_service import ProjectService
from app.services.sprint_service import SprintService
from app.services.story_service import StoryService
from app.services.ticket_service import TicketService

T = TypeVar("T")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session for MCP tools.
    
    Manages session lifecycle independently from FastAPI's dependency injection.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_project_service() -> AsyncGenerator[ProjectService, None]:
    """Get a ProjectService instance with its own DB session."""
    async with get_db_session() as session:
        yield ProjectService(session)


@asynccontextmanager
async def get_epic_service() -> AsyncGenerator[EpicService, None]:
    """Get an EpicService instance with its own DB session."""
    async with get_db_session() as session:
        yield EpicService(session)


@asynccontextmanager
async def get_story_service() -> AsyncGenerator[StoryService, None]:
    """Get a StoryService instance with its own DB session."""
    async with get_db_session() as session:
        yield StoryService(session)


@asynccontextmanager
async def get_sprint_service() -> AsyncGenerator[SprintService, None]:
    """Get a SprintService instance with its own DB session."""
    async with get_db_session() as session:
        yield SprintService(session)


@asynccontextmanager
async def get_comment_service() -> AsyncGenerator[CommentService, None]:
    """Get a CommentService instance with its own DB session."""
    async with get_db_session() as session:
        yield CommentService(session)


@asynccontextmanager
async def get_ticket_service() -> AsyncGenerator[TicketService, None]:
    """Get a TicketService instance with its own DB session."""
    async with get_db_session() as session:
        yield TicketService(session)


@asynccontextmanager
async def get_document_service() -> AsyncGenerator[DocumentService, None]:
    """Get a DocumentService instance with its own DB session."""
    async with get_db_session() as session:
        yield DocumentService(session)


def serialize_response(obj: object) -> str:
    """
    Serialize a Pydantic model or dict to JSON string for MCP tool responses.
    
    Args:
        obj: Object to serialize (Pydantic model, dict, list, etc.)
        
    Returns:
        JSON string
    """
    if hasattr(obj, "model_dump"):
        data = obj.model_dump()
    elif isinstance(obj, list):
        data = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in obj
        ]
    else:
        data = obj
    
    return json.dumps(data, default=_json_serializer, ensure_ascii=False, indent=2)


def _json_serializer(obj: object) -> str:
    """Handle non-serializable types for JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
