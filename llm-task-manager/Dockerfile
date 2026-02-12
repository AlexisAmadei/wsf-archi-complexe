# =============================================================================
# Multi-stage Dockerfile for LLM Task Manager
# Builds two targets: API (FastAPI) and MCP (standalone server)
#
# Usage:
#   docker build --target api -t llm-task-manager-api .
#   docker build --target mcp -t llm-task-manager-mcp .
# =============================================================================

# ---------------------
# Base stage: shared dependencies
# ---------------------
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency file
COPY pyproject.toml ./

# Install Python dependencies
RUN uv pip install --system --no-cache-dir .

# Copy source code
COPY app/ ./app/
COPY mcp_server/ ./mcp_server/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# ---------------------
# API target: FastAPI REST API
# ---------------------
FROM base AS api

EXPOSE 8080

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

# ---------------------
# MCP target: Standalone MCP Server (SSE)
# ---------------------
FROM base AS mcp

EXPOSE 8001

ENV PORT=8001
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "mcp_server", "--transport", "sse"]
