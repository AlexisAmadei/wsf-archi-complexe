# Image Python officielle legere
FROM python:3.11-slim

# Repertoire de travail
WORKDIR /app

# Installer uv depuis l'image officielle
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copier les fichiers de configuration (cache Docker layer)
COPY pyproject.toml ./

# Installation des dependances avec uv
RUN uv sync --frozen --no-dev || uv pip install --system --no-cache .

# Copie du code source et alembic
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Exposition du port 8080 (standard Cloud Run)
EXPOSE 8080

# Commande de demarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
