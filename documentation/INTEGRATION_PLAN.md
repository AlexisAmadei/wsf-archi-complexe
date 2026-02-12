# Plan d'Intégration - LLM Task Manager

Ce document présente le plan détaillé de réalisation du projet LLM Task Manager, structuré en 8 phases avec 11 étapes principales.

---

## Phase 1 : Configuration de l'environnement et infrastructure de base

### Étape 1.1 : Setup du projet Python
- Initialiser le projet avec `uv`
- Configurer `pyproject.toml` avec les dépendances (FastAPI, SQLAlchemy, Pydantic, MCP SDK, asyncpg, etc.)
- Créer la structure de dossiers selon `documentation/TREE.md`
- Configurer les outils de développement (ruff, pytest)

**Dépendances principales** :
- FastAPI (API REST)
- SQLAlchemy 2.0+ avec asyncpg (ORM asynchrone)
- Pydantic v2 (validation)
- mcp (SDK MCP officiel)
- alembic (migrations)
- pytest, pytest-asyncio (tests)
- python-jose[cryptography], passlib[bcrypt] (JWT)
- uvicorn (serveur ASGI)

### Étape 1.2 : Configuration de la base de données locale
- Configurer PostgreSQL en local (Docker Compose pour le dev)
- Créer le fichier `app/database.py` avec la connexion asyncpg
- Initialiser Alembic pour les migrations dans `alembic/`
- Configurer `app/config.py` pour gérer les variables d'environnement

**Variables d'environnement requises** :
- `DATABASE_URL` : URL de connexion PostgreSQL
- `JWT_SECRET_KEY` : Secret pour les tokens JWT
- `JWT_ALGORITHM` : Algorithme JWT (HS256)
- `ENVIRONMENT` : dev/staging/production

---

## Phase 2 : Modèles de données et migrations

### Étape 2.1 : Définition des modèles SQLAlchemy
Créer les modèles dans `app/models/` :
- `project.py` : Projet (id, name, description, created_at)
- `epic.py` : Epic (id, project_id, title, description, status, created_at, updated_at)
- `story.py` : Story (id, epic_id, title, description, status, priority, story_points, assignee, created_at, updated_at)
- `sprint.py` : Sprint (id, project_id, name, goal, start_date, end_date, status, created_at)
- `comment.py` : Comment (id, entity_type, entity_id, content, author, created_at)
- `document.py` : Document (id, project_id, title, content, template_type, created_at, updated_at)

**Contraintes SQL à implémenter** :
- **BR-01** : CHECK constraint sur `story.story_points` (NULL ou valeur Fibonacci)
- **BR-02** : Machine à états dans l'application (validée côté Python)
- **BR-03** : UNIQUE INDEX partiel sur `story_sprint` avec `WHERE sprint.status = 'active'`
- **BR-04** : Validation applicative avant clôture de sprint

**Relations** :
- Project 1-N Epic
- Epic 1-N Story
- Project 1-N Sprint
- Story N-N Sprint (table d'association `story_sprint` avec historique)
- Comment polymorphique (entity_type + entity_id)
- Project 1-N Document

### Étape 2.2 : Schémas Pydantic
Créer les schémas de validation dans `app/schemas/` :
- Schémas Create (requête de création)
- Schémas Update (requête de modification partielle)
- Schémas Response (réponse API)
- Schémas List (liste avec pagination)

**Validateurs custom** :
- Fibonacci validator pour `story_points` : `[None, 1, 2, 3, 5, 8, 13, 21]`
- Enum pour `status` : Epic (todo/in_progress/done), Story (backlog/todo/in_progress/in_review/done)
- Enum pour `priority` : low/medium/high/critical
- Validator de transition de statut (BR-02)

### Étape 2.3 : Migrations initiales
- Générer la migration Alembic pour créer toutes les tables
- Créer les indexes (performance sur les recherches)
- Créer le script `scripts/seed_templates.py` pour les templates de documents :
  - Problem Statement
  - Product Vision
  - Technical Decision Record
  - Sprint Retrospective

---

## Phase 3 : Logique métier (Services)

### Étape 3.1 : Moteur de règles métier
Créer le module `app/services/rules_engine.py` :

**BR-01 : Validation Fibonacci**
```python
FIBONACCI_VALUES = [None, 1, 2, 3, 5, 8, 13, 21]

def validate_story_points(points: int | None) -> bool:
    return points in FIBONACCI_VALUES
```

**BR-02 : Machine à états pour Story**
```python
STORY_TRANSITIONS = {
    "backlog": ["todo"],
    "todo": ["in_progress", "backlog"],
    "in_progress": ["in_review", "todo"],
    "in_review": ["done", "in_progress"],
    "done": []  # Terminal
}

def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in STORY_TRANSITIONS.get(from_status, [])
```

**BR-03 : Unicité de sprint actif**
- Une story ne peut être assignée qu'à UN SEUL sprint avec `status='active'`
- Implémenté via UNIQUE INDEX partiel en SQL + validation Python

**BR-04 : Règles de clôture de sprint**
```python
def can_close_sprint(sprint: Sprint, stories: list[Story]) -> tuple[bool, str]:
    # Vérifier qu'il n'y a pas de stories en cours
    in_progress = [s for s in stories if s.status in ["in_progress", "in_review"]]
    if in_progress:
        return False, f"{len(in_progress)} stories still in progress"
    return True, ""
```

### Étape 3.2 : Services métier
Implémenter dans `app/services/` :
- `project_service.py` : create, get, list
- `epic_service.py` : create, get, update, list, search, filter_by_status
- `story_service.py` : create, get, update, list, search, filter, transition_status
- `sprint_service.py` : create, start, close, assign_story, remove_story
- `comment_service.py` : add, list_for_entity
- `document_service.py` : create, get, update, list, search, load_template

**Architecture du service** :
```python
class StoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rules = RulesEngine()
    
    async def transition_status(self, story_id: str, new_status: str) -> Story:
        story = await self.get(story_id)
        if not self.rules.can_transition(story.status, new_status):
            raise BusinessRuleViolation(f"Cannot transition from {story.status} to {new_status}")
        story.status = new_status
        await self.db.commit()
        return story
```

---

## Phase 4 : API REST

### Étape 4.1 : Configuration FastAPI
- Configurer `app/main.py` avec les middleware, CORS, exception handlers
- Créer `app/security.py` pour la gestion JWT (optionnel pour la démo, mais bonne pratique)
- Implémenter `app/api/deps.py` pour les dépendances :
  - `get_db()` : Session de base de données
  - `get_current_user()` : Authentification (optionnel)

**Structure de `main.py`** :
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, projects, epics, stories, sprints, comments, documents

app = FastAPI(title="LLM Task Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(epics.router, prefix="/api/v1/epics", tags=["epics"])
app.include_router(stories.router, prefix="/api/v1/stories", tags=["stories"])
app.include_router(sprints.router, prefix="/api/v1/sprints", tags=["sprints"])
app.include_router(comments.router, prefix="/api/v1/comments", tags=["comments"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
```

### Étape 4.2 : Endpoints REST
Créer les routers dans `app/api/` :

**`health.py`** : Endpoint `/health`
- GET `/health` : Vérifier l'état du service et la connexion DB

**`projects.py`** :
- POST `/api/v1/projects` : Créer un projet
- GET `/api/v1/projects` : Lister les projets
- GET `/api/v1/projects/{project_id}` : Détails d'un projet

**`epics.py`** :
- POST `/api/v1/epics` : Créer un epic
- GET `/api/v1/epics/{epic_id}` : Détails d'un epic
- PATCH `/api/v1/epics/{epic_id}` : Modifier un epic
- GET `/api/v1/epics` : Lister les epics (avec filtres `?project_id=&status=`)
- GET `/api/v1/epics/search` : Rechercher par mot-clé (`?q=keyword`)

**`stories.py`** :
- POST `/api/v1/stories` : Créer une story
- GET `/api/v1/stories/{story_id}` : Détails d'une story
- PATCH `/api/v1/stories/{story_id}` : Modifier une story
- POST `/api/v1/stories/{story_id}/transition` : Changer le statut
- GET `/api/v1/stories` : Lister les stories (avec filtres `?epic_id=&status=&priority=&assignee=&sprint_id=`)
- GET `/api/v1/stories/search` : Rechercher par mot-clé

**`sprints.py`** :
- POST `/api/v1/sprints` : Créer un sprint
- GET `/api/v1/sprints/{sprint_id}` : Détails d'un sprint
- POST `/api/v1/sprints/{sprint_id}/start` : Démarrer un sprint
- POST `/api/v1/sprints/{sprint_id}/close` : Clôturer un sprint
- POST `/api/v1/sprints/{sprint_id}/stories` : Assigner une story
- DELETE `/api/v1/sprints/{sprint_id}/stories/{story_id}` : Retirer une story
- GET `/api/v1/sprints` : Lister les sprints

**`comments.py`** :
- POST `/api/v1/comments` : Ajouter un commentaire
- GET `/api/v1/comments` : Lister les commentaires (`?entity_type=&entity_id=`)

**`documents.py`** :
- POST `/api/v1/documents` : Créer un document (avec ou sans template)
- GET `/api/v1/documents/{document_id}` : Lire un document
- PATCH `/api/v1/documents/{document_id}` : Modifier un document
- GET `/api/v1/documents` : Lister les documents (`?project_id=&template_type=`)
- GET `/api/v1/documents/search` : Rechercher dans les documents

---

## Phase 5 : Serveur MCP

### Étape 5.1 : Configuration du serveur MCP
- Créer `mcp_server/server.py` avec initialisation SSE
- Créer `mcp_server/shared_services.py` pour l'accès aux services métier

**Structure de `server.py`** :
```python
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp_server.tools import (
    project_tools, epic_tools, story_tools, 
    sprint_tools, comment_tools, document_tools
)

app = Server("llm-task-manager")

# Enregistrer tous les tools
project_tools.register(app)
epic_tools.register(app)
story_tools.register(app)
sprint_tools.register(app)
comment_tools.register(app)
document_tools.register(app)

# Exposer via SSE
async def run_sse():
    async with SseServerTransport("/mcp/sse") as transport:
        await app.run(transport)
```

### Étape 5.2 : Implémentation des tools MCP
Créer les tools dans `mcp_server/tools/` :

**`project_tools.py`** :
- `create_project(name, description)` → project_id
- `list_projects()` → [projects]

**`epic_tools.py`** :
- `create_epic(project_id, title, description)` → epic_id
- `get_epic(epic_id)` → epic_details
- `update_epic(epic_id, title?, description?, status?)` → updated_epic
- `list_epics(project_id?, status?)` → [epics]
- `search_epics(keyword)` → [epics]

**`story_tools.py`** :
- `create_story(epic_id, title, description, priority?, story_points?)` → story_id
- `get_story(story_id)` → story_details
- `update_story(story_id, title?, description?, priority?, story_points?, assignee?)` → updated_story
- `transition_story_status(story_id, new_status)` → updated_story
- `list_stories(epic_id?, status?, priority?, assignee?, sprint_id?)` → [stories]
- `search_stories(keyword)` → [stories]

**`sprint_tools.py`** :
- `create_sprint(project_id, name, goal, start_date?, end_date?)` → sprint_id
- `start_sprint(sprint_id)` → updated_sprint
- `close_sprint(sprint_id)` → closed_sprint
- `assign_story_to_sprint(sprint_id, story_id)` → success
- `remove_story_from_sprint(sprint_id, story_id)` → success
- `list_sprints(project_id?, status?)` → [sprints]

**`comment_tools.py`** :
- `add_comment(entity_type, entity_id, content, author)` → comment_id
- `list_comments(entity_type, entity_id)` → [comments]

**`document_tools.py`** :
- `create_document(project_id, title, template_type?)` → document_id
- `get_document(document_id)` → document_content
- `update_document(document_id, title?, content?)` → updated_document
- `list_documents(project_id?, template_type?)` → [documents]
- `search_documents(keyword)` → [documents]

**Exemple de tool avec docstring optimisée pour LLM** :
```python
@app.tool()
async def create_story(
    epic_id: str,
    title: str,
    description: str,
    priority: str = "medium",
    story_points: int | None = None
) -> dict:
    """Create a new user story in an epic.
    
    Use this tool when the user wants to:
    - Add a new feature or task to an epic
    - Break down an epic into smaller pieces
    - Create a story from a conversation
    
    Args:
        epic_id: The ID of the parent epic (required)
        title: Short title for the story (required)
        description: Detailed description in markdown (required)
        priority: Priority level - one of: low, medium, high, critical (default: medium)
        story_points: Estimate using Fibonacci sequence: 1, 2, 3, 5, 8, 13, 21 (optional)
    
    Returns:
        The created story with its ID and initial status (backlog)
    
    Example:
        create_story(
            epic_id="epic_123",
            title="Add user authentication",
            description="Implement JWT-based auth with refresh tokens",
            priority="high",
            story_points=5
        )
    """
    # Implementation...
```

### Étape 5.3 : Intégration MCP dans FastAPI
- Monter le serveur MCP sur `/mcp/sse` dans `app/main.py`
- Assurer la réutilisation des services métier entre REST et MCP
- Configurer les headers CORS pour SSE

---

## Phase 6 : Tests

### Étape 6.1 : Tests unitaires
- Configurer pytest dans `tests/conftest.py` avec fixtures (DB test, client HTTP)
- Créer les tests unitaires dans `tests/unit/` :

**`test_models.py`** :
- Validation Pydantic des schémas
- Contraintes sur les champs

**`test_schemas.py`** :
- Sérialisation/désérialisation
- Validators custom

**`test_services.py`** :
- Logique métier isolée (avec mock DB)
- CRUD operations

**`test_business_rules.py`** :
- BR-01 : Story points uniquement Fibonacci
- BR-02 : Transitions de statut valides/invalides
- BR-03 : Assignation à un seul sprint actif
- BR-04 : Clôture de sprint avec stories en cours

### Étape 6.2 : Tests d'intégration
Créer les tests dans `tests/integration/` :

**`test_api_crud.py`** :
- Cycles CRUD complets via REST API
- Tests de tous les endpoints avec DB réelle (testcontainers ou SQLite)

**`test_story_workflow.py`** :
- Cycle de vie complet d'une story : backlog → todo → in_progress → in_review → done
- Tentatives de transitions illégales

**`test_mcp_tools.py`** :
- Appels MCP avec assertions sur les réponses
- Scénarios bout-en-bout

**Couverture cible** : > 80% sur les services et règles métier

---

## Phase 7 : Déploiement GCP

### Étape 7.1 : Configuration Cloud SQL
**Provisionnement** :
```bash
gcloud sql instances create llm-task-manager-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=europe-west1 \
  --storage-auto-increase \
  --backup-start-time=03:00
```

**Créer la base de données** :
```bash
gcloud sql databases create llm_task_manager \
  --instance=llm-task-manager-db
```

**Créer un utilisateur** :
```bash
gcloud sql users create app_user \
  --instance=llm-task-manager-db \
  --password=<strong-password>
```

**Tester la connexion via Cloud SQL Proxy** :
```bash
cloud-sql-proxy --port 5432 <PROJECT_ID>:europe-west1:llm-task-manager-db &
psql -h localhost -U app_user -d llm_task_manager
```

### Étape 7.2 : Conteneurisation
**Créer le `Dockerfile`** :
```dockerfile
FROM python:3.11-slim

# Installer uv
RUN pip install uv

WORKDIR /app

# Copier les fichiers de dépendances
COPY pyproject.toml ./

# Installer les dépendances
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# Copier le code source
COPY . .

# Exposer le port
EXPOSE 8080

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Créer `.dockerignore`** :
```
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.coverage
htmlcov
.env
.venv
venv
tests
*.md
.git
.gitignore
Dockerfile
.dockerignore
cloudbuild.yaml
```

**Tester le build local** :
```bash
docker build -t llm-task-manager:local .
docker run -p 8080:8080 -e DATABASE_URL=... llm-task-manager:local
```

### Étape 7.3 : Pipeline Cloud Build
**Créer `cloudbuild.yaml`** :
```yaml
steps:
  # Build de l'image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api:$COMMIT_SHA'
      - '-t'
      - 'europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api:latest'
      - '.'
    dir: 'llm-task-manager'

  # Exécuter les tests
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'run'
      - 'europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api:$COMMIT_SHA'
      - 'pytest'
      - 'tests/'

  # Push vers Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - 'europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api'

  # Déploiement sur Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'llm-task-manager'
      - '--image'
      - 'europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api:$COMMIT_SHA'
      - '--region'
      - 'europe-west1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--set-env-vars'
      - 'ENVIRONMENT=production'
      - '--set-secrets'
      - 'DATABASE_URL=llm-task-manager-db-url:latest,JWT_SECRET_KEY=jwt-secret:latest'
      - '--add-cloudsql-instances'
      - '$PROJECT_ID:europe-west1:llm-task-manager-db'

options:
  logging: CLOUD_LOGGING_ONLY

images:
  - 'europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api:$COMMIT_SHA'
  - 'europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api:latest'
```

**Configurer Secret Manager** :
```bash
# Créer les secrets
echo -n "postgresql+asyncpg://app_user:PASSWORD@/llm_task_manager?host=/cloudsql/PROJECT_ID:europe-west1:llm-task-manager-db" | \
  gcloud secrets create llm-task-manager-db-url --data-file=-

echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create jwt-secret --data-file=-

# Donner accès à Cloud Run
gcloud secrets add-iam-policy-binding llm-task-manager-db-url \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding jwt-secret \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Étape 7.4 : Déploiement initial
**Créer l'Artifact Registry** :
```bash
gcloud artifacts repositories create llm-task-manager \
  --repository-format=docker \
  --location=europe-west1 \
  --description="LLM Task Manager Docker images"
```

**Lancer le premier déploiement** :
```bash
gcloud builds submit --config=cloudbuild.yaml
```

**Vérifier le déploiement** :
```bash
SERVICE_URL=$(gcloud run services describe llm-task-manager \
  --region=europe-west1 \
  --format='value(status.url)')

curl $SERVICE_URL/health
```

**Exécuter les migrations Alembic** :
Option 1 - Via un job Cloud Run :
```bash
gcloud run jobs create llm-task-manager-migrate \
  --image=europe-west1-docker.pkg.dev/$PROJECT_ID/llm-task-manager/api:latest \
  --region=europe-west1 \
  --command="alembic" \
  --args="upgrade,head" \
  --add-cloudsql-instances=$PROJECT_ID:europe-west1:llm-task-manager-db \
  --set-secrets=DATABASE_URL=llm-task-manager-db-url:latest

gcloud run jobs execute llm-task-manager-migrate --region=europe-west1
```

Option 2 - Via Cloud SQL Proxy en local :
```bash
cloud-sql-proxy $PROJECT_ID:europe-west1:llm-task-manager-db &
export DATABASE_URL="postgresql+asyncpg://app_user:PASSWORD@localhost/llm_task_manager"
alembic upgrade head
```

**Seed les templates** :
```bash
python scripts/seed_templates.py
```

---

## Phase 8 : Documentation et démo

### Étape 8.1 : Documentation
Compléter le `README.md` avec :

**Setup local** :
```bash
# Cloner le repo
git clone <repo-url>
cd llm-task-manager

# Installer les dépendances avec uv
uv pip install -e .

# Lancer PostgreSQL avec Docker
docker-compose up -d

# Exécuter les migrations
alembic upgrade head

# Seed les templates
python scripts/seed_templates.py

# Lancer le serveur
uvicorn app.main:app --reload
```

**Variables d'environnement** :
- `DATABASE_URL` : `postgresql+asyncpg://user:pass@localhost/db`
- `JWT_SECRET_KEY` : Secret pour JWT
- `JWT_ALGORITHM` : `HS256`
- `ENVIRONMENT` : `dev`

**Exemples d'utilisation REST** :
```bash
# Créer un projet
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "description": "Test project"}'

# Créer un epic
curl -X POST http://localhost:8000/api/v1/epics \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj_123", "title": "User Auth", "description": "Implement authentication"}'
```

**Configuration MCP pour Claude Desktop** :
```json
{
  "mcpServers": {
    "llm-task-manager": {
      "url": "https://llm-task-manager-xyz.run.app/mcp/sse"
    }
  }
}
```

### Étape 8.2 : Préparation de la démo
**Créer un jeu de données de test** :
```bash
# Script de seed démo
python scripts/seed_demo.py
```

Contenu :
- 1 projet "AI Assistant Platform"
- 3 epics : "User Management", "Task Operations", "MCP Integration"
- 8 stories réparties dans les epics
- 2 sprints : 1 actif, 1 terminé
- Quelques commentaires et documents

**Scénarios de démonstration REST** :
1. Créer un projet et un epic
2. Créer plusieurs stories avec différentes priorités
3. Transition d'une story à travers les statuts
4. Créer et démarrer un sprint
5. Assigner des stories au sprint
6. Ajouter des commentaires
7. Créer un document depuis un template

**Scénarios de démonstration MCP** :
Depuis Claude Desktop ou Cursor :
1. "Show me all projects"
2. "Create a new story in epic X for implementing OAuth"
3. "What stories are in the current sprint?"
4. "Move story Y to in_progress"
5. "Add a comment to story Z mentioning the PR is ready"
6. "Create a Technical Decision Record for using GraphQL"

**Questions architecturales potentielles** :
- Pourquoi FastAPI plutôt que Flask/Django ?
- Pourquoi SQLAlchemy async plutôt que sync ?
- Comment gérez-vous la concurrence sur les updates ?
- Comment sécurisez-vous les endpoints MCP ?
- Quelle est votre stratégie de versioning d'API ?
- Comment gérez-vous les migrations en production sans downtime ?
- Pourquoi Cloud Run plutôt que GKE ou Compute Engine ?

---

## Critères de validation

### Phase 1-2 (Infrastructure + Données)
- ✅ PostgreSQL connecté et migrations exécutées
- ✅ Tous les modèles créés avec relations
- ✅ Contraintes SQL implémentées (CHECK, UNIQUE INDEX)
- ✅ Schémas Pydantic avec validators

### Phase 3-4 (Services + API)
- ✅ Les 4 business rules sont validées
- ✅ CRUD complet sur les 6 entités
- ✅ API REST avec tous les endpoints fonctionnels
- ✅ OpenAPI docs générées automatiquement

### Phase 5 (MCP)
- ✅ Serveur MCP exposé sur `/mcp/sse`
- ✅ Tous les tools MCP implémentés et documentés
- ✅ Réutilisation des services métier (pas de duplication)
- ✅ Testable depuis Claude Desktop/Cursor

### Phase 6 (Tests)
- ✅ Tests unitaires sur les business rules
- ✅ Tests d'intégration sur les workflows
- ✅ Couverture > 80%
- ✅ CI qui lance les tests

### Phase 7 (Déploiement)
- ✅ Cloud SQL provisionné et accessible
- ✅ Service déployé sur Cloud Run
- ✅ URL publique fonctionnelle
- ✅ CI/CD avec Cloud Build
- ✅ Secrets dans Secret Manager

### Phase 8 (Documentation)
- ✅ README complet avec setup local et déploiement
- ✅ ARCHITECTURE.md avec les 5 domaines TOGAF
- ✅ Données de démo seed
- ✅ Scénarios de démo préparés

---

## Livrables finaux

1. **Repo GitHub** :
   - Code source complet
   - `ARCHITECTURE.md` avec les 5 domaines TOGAF
   - `README.md` avec instructions
   - `cloudbuild.yaml` configuré

2. **Service déployé** :
   - URL Cloud Run publique
   - Endpoint `/health` fonctionnel
   - API REST accessible
   - MCP endpoint `/mcp/sse` accessible

3. **Démo fonctionnelle** :
   - Scénarios REST préparés
   - Connexion MCP depuis Claude Desktop
   - Jeu de données de test

---

## Commandes rapides

```bash
# Setup local
uv pip install -e .
docker-compose up -d
alembic upgrade head
python scripts/seed_templates.py
uvicorn app.main:app --reload

# Tests
pytest tests/ -v --cov=app

# Build Docker
docker build -t llm-task-manager .

# Déploiement GCP
gcloud builds submit --config=cloudbuild.yaml

# Vérifier le service
curl https://llm-task-manager-xyz.run.app/health
```

---

**Date de création** : 2026-02-12  
**Version** : 1.0  
**Auteur** : Plan d'intégration généré pour le TP Final Architecture Technique Complexe
