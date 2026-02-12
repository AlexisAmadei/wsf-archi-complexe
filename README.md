# wsf-archi-complexe

# LLM Task Manager

Gestionnaire de projet agile (type Jira) exposé via **API REST** (FastAPI) et **serveur MCP** (Model Context Protocol) standalone.

## Architecture

```
┌──────────────┐       ┌──────────────────┐
│  API FastAPI  │       │  Serveur MCP SSE │
│  (port 8080)  │       │  (port 8001)     │
└──────┬───────┘       └───────┬──────────┘
       │                       │
       │   ┌───────────────┐   │
       └──►│  Services      │◄──┘
           │  métier (app/) │
           └───────┬───────┘
                   │
           ┌───────▼───────┐
           │  Cloud SQL     │
           │  PostgreSQL    │
           └───────────────┘
```

Deux processus indépendants, mêmes services, même base de données.

---

## Déploiement GCP — Commandes utilisées

### 1. Authentification

```bash
# Authentifier Docker vers Artifact Registry
gcloud auth configure-docker europe-west1-docker.pkg.dev --quiet
```

### 2. Build des images Docker (multi-target)

```bash
# Build API
docker build --target api -t europe-west1-docker.pkg.dev/<PROJECT_ID>/llm-task-manager/api:latest .

# Build MCP
docker build --target mcp -t europe-west1-docker.pkg.dev/<PROJECT_ID>/llm-task-manager/mcp:latest .
```

### 3. Push vers Artifact Registry

```bash
docker push europe-west1-docker.pkg.dev/<PROJECT_ID>/llm-task-manager/api:latest
docker push europe-west1-docker.pkg.dev/<PROJECT_ID>/llm-task-manager/mcp:latest
```

### 4. Déploiement Cloud Run — MCP Server

```bash
gcloud run deploy llm-task-manager-mcp \
  --image=europe-west1-docker.pkg.dev/<PROJECT_ID>/llm-task-manager/mcp:latest \
  --region=europe-west1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8001 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="DATABASE_URL=llm-task-manager-db-url:latest,JWT_SECRET_KEY=jwt-secret:latest" \
  --add-cloudsql-instances=<PROJECT_ID>:europe-west1:llm-task-manager-db \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --session-affinity \
  --project=<PROJECT_ID>
```

### 5. Déploiement Cloud Run — API REST

```bash
gcloud run deploy llm-task-manager-api \
  --image=europe-west1-docker.pkg.dev/<PROJECT_ID>/llm-task-manager/api:latest \
  --region=europe-west1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="DATABASE_URL=llm-task-manager-db-url:latest,JWT_SECRET_KEY=jwt-secret:latest" \
  --add-cloudsql-instances=<PROJECT_ID>:europe-west1:llm-task-manager-db \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --project=<PROJECT_ID>
```

### 6. CI/CD — Cloud Build (tout-en-un)

```bash
gcloud builds submit --config=cloudbuild.yaml
```

---

## Configuration MCP Client

### Cursor (`.vscode/settings.json`)

```json
{
  "mcpServers": {
    "llm-task-manager": {
      "url": "https://llm-task-manager-mcp-<ID>.europe-west1.run.app/sse"
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "llm-task-manager": {
      "url": "https://llm-task-manager-mcp-<ID>.europe-west1.run.app/sse"
    }
  }
}
```

---

## Lancer en local

```bash
# API REST
uvicorn app.main:app --host 0.0.0.0 --port 8080

# MCP Server (SSE)
python -m mcp_server --transport sse

# MCP Server (stdio, pour tests locaux)
python -m mcp_server
```

---

## Bugs corrigés lors du déploiement

| Problème | Cause | Fix |
|---|---|---|
| `FastMCP.__init__() got unexpected keyword argument 'version'` | API MCP SDK v1.26 n'accepte pas `version` | Remplacé par `instructions` |
| `'function' object is not subscriptable` (`list[Epic]`) | Python 3.11 conflit entre `list` builtin et méthode `list()` | Ajout `from __future__ import annotations` dans les 6 services |
