"""
Health check endpoint.

Provides service status and database connectivity verification.
"""

from fastapi import APIRouter

from app.config import settings
from app.database import check_db_connection

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """
    Check service health and database connectivity.

    Returns:
        Health status with service info and DB connection state
    """
    db_connected = await check_db_connection()

    return {
        "status": "healthy" if db_connected else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_connected else "disconnected",
    }
