"""
FastAPI application entrypoint.

Configures middleware, exception handlers, and routes.
"""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import comments, documents, epics, health, projects, sprints, stories
from app.config import settings
from app.database import close_db, init_db
from app.exceptions import BusinessRuleViolation, EntityNotFound, NotFoundError, ValidationError
from app.security import verify_token


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Task management API with MCP integration for LLM-powered project management.",
    lifespan=lifespan,
)


# --- JWT Authentication Middleware ---

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT authentication middleware for REST API.

    Validates Bearer tokens on all requests except health checks.
    Can be disabled via API_DISABLE_AUTH environment variable (dev only).
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health checks
        if request.url.path in ["/health", "/", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Skip auth if disabled (dev only)
        if os.environ.get("API_DISABLE_AUTH", "false").lower() == "true":
            return await call_next(request)

        # OPTIONS requests don't need auth
        if request.method == "OPTIONS":
            return await call_next(request)

        # Verify JWT token
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header. Use 'Bearer <token>'"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.replace("Bearer ", "")
        payload = verify_token(token)

        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Store user info in request state
        request.state.user = {
            "user_id": payload.get("sub"),
            "role": payload.get("role", "contributor"),
            "permissions": payload.get("permissions", []),
        }

        return await call_next(request)


# Add JWT middleware
app.add_middleware(JWTAuthMiddleware)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Exception Handlers ---

@app.exception_handler(NotFoundError)
@app.exception_handler(EntityNotFound)
async def not_found_handler(request: Request, exc: EntityNotFound) -> JSONResponse:
    """Handle entity not found errors → 404."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(BusinessRuleViolation)
async def business_rule_handler(request: Request, exc: BusinessRuleViolation) -> JSONResponse:
    """Handle business rule violations → 409 Conflict."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors → 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle value errors (e.g., invalid template type) → 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# --- Routers ---

app.include_router(health.router, tags=["health"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(epics.router, prefix="/api/v1/epics", tags=["epics"])
app.include_router(stories.router, prefix="/api/v1/stories", tags=["stories"])
app.include_router(sprints.router, prefix="/api/v1/sprints", tags=["sprints"])
app.include_router(comments.router, prefix="/api/v1/comments", tags=["comments"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
