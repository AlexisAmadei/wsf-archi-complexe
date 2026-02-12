# wsf-archi-complexe

# LLM Task Manager

Gestionnaire de projet agile (type Jira) exposé via **API REST** (FastAPI) et **serveur MCP** (Model Context Protocol) standalone.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Clients MCP (Claude, VS Code, Cursor)                  │
│  Authorization: Bearer <JWT Token>                       │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTPS + SSE
                     ▼
┌────────────────────────────────────────────────────────┐
│             Cloud Run (GCP)                            │
│  ┌──────────────┐       ┌──────────────────┐          │
│  │  API FastAPI │       │  Serveur MCP SSE │          │
│  │  (port 8080) │       │  (port 8001)     │          │
│  │              │       │  + AuthMiddleware│          │
│  └──────┬───────┘       └───────┬──────────┘          │
│         │                       │                      │
│         │   ┌───────────────┐   │                      │
│         └──►│  Services     │◄──┘                      │
│             │  métier (app/)│                          │
│             └───────┬───────┘                          │
│                     │                                  │
│             ┌───────▼───────┐                          │
│             │  Cloud SQL    │                          │
│             │  PostgreSQL   │                          │
│             └───────────────┘                          │
└────────────────────────────────────────────────────────┘

Secrets (Secret Manager):
- JWT_SECRET_KEY : clé de signature des tokens JWT
- DATABASE_URL : connexion PostgreSQL via Unix socket
```

**Authentification :**
- API REST : JWT Bearer (optionnel, pour futures fonctionnalités)
- Serveur MCP : JWT Bearer **obligatoire** via header Authorization
- Validation : `AuthMiddleware` → `verify_jwt_token()` → permissions par rôle

Deux processus indépendants, mêmes services, même base de données.

---

## Déploiement GCP — Commandes utilisées

### 0. Prérequis : Configuration des secrets

```bash
# Créer le secret JWT (générer une clé sécurisée)
echo -n "$(openssl rand -base64 32)" | gcloud secrets create jwt-secret --data-file=-

# Créer le secret DATABASE_URL
echo -n "postgresql+asyncpg://user:password@/dbname?host=/cloudsql/PROJECT_ID:REGION:INSTANCE" \
  | gcloud secrets create llm-task-manager-db-url --data-file=-

# Vérifier les secrets
gcloud secrets list
```

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
# Déploie automatiquement API + MCP avec JWT authentication
gcloud builds submit --config=cloudbuild.yaml
```

**Note :** Le serveur MCP exige désormais une authentification JWT via le header `Authorization: Bearer <token>`. Voir la section "Configuration MCP Client avec JWT" ci-dessus.

---

## Configuration MCP Client avec JWT

### 1. Générer un token JWT

```bash
cd llm-task-manager

# Activer l'environnement virtuel
source .venv/bin/activate  # ou .venv\Scripts\activate sur Windows

# Générer un token admin (90 jours)
python scripts/generate_mcp_token.py --user-id "votre@email.com" --role admin --expires 90

# Générer un token contributeur (30 jours par défaut)
python scripts/generate_mcp_token.py --user-id "user@example.com" --role contributor

# Output direct en JSON pour copier-coller
python scripts/generate_mcp_token.py --user-id "user@example.com" --role admin --json
```

**Rôles disponibles :**
- `admin` : Accès complet (CRUD sur toutes les ressources)
- `contributor` : Lecture + création/mise à jour des stories et commentaires
- `viewer` : Lecture seule

### 2. Configuration VS Code (`.vscode/mcp.json`)

```json
{
  "servers": {
    "llmTaskManager": {
      "type": "sse",
      "url": "https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse",
      "headers": {
        "Authorization": "Bearer VOTRE_TOKEN_JWT_ICI"
      }
    }
  }
}
```

### 3. Configuration Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "llm-task-manager": {
      "url": "https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse",
      "headers": {
        "Authorization": "Bearer VOTRE_TOKEN_JWT_ICI"
      }
    }
  }
}
```

⚠️ **Sécurité :** Ne commitez JAMAIS vos tokens JWT dans Git. Ajoutez `.vscode/mcp.json` au `.gitignore`.

---

## Lancer en local

### Avec authentification JWT (production-like)

```bash
cd llm-task-manager
source .venv/bin/activate

# Définir le secret JWT (même que celui en production)
export JWT_SECRET_KEY="votre-secret-key-secure"
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/llm_task_manager"

# API REST
uvicorn app.main:app --host 0.0.0.0 --port 8080

# MCP Server (SSE avec JWT)
python -m mcp_server --transport sse
```

### Sans authentification (développement local uniquement)

```bash
cd llm-task-manager
source .venv/bin/activate

# Désactiver l'authentification JWT
export MCP_DISABLE_AUTH=true
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/llm_task_manager"

# MCP Server (stdio, pour tests locaux)
python -m mcp_server

# MCP Server (SSE sans auth)
python -m mcp_server --transport sse
```

⚠️ **Ne JAMAIS utiliser `MCP_DISABLE_AUTH=true` en production !**

---

## Test de l'authentification JWT

### Vérifier que l'authentification fonctionne

```bash
# Sans token (doit retourner 401)
curl https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse

# Avec token valide (doit retourner 200)
curl -H "Authorization: Bearer VOTRE_TOKEN_JWT" \
  https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse

# Générer un token de test
cd llm-task-manager
.venv/bin/python scripts/generate_mcp_token.py --user-id "test@example.com" --role admin --expires 1
```

### Test des permissions par rôle

```bash
# Token admin : peut tout faire
python scripts/generate_mcp_token.py --user-id "admin@example.com" --role admin

# Token contributor : lecture + création stories
python scripts/generate_mcp_token.py --user-id "dev@example.com" --role contributor

# Token viewer : lecture seule
python scripts/generate_mcp_token.py --user-id "viewer@example.com" --role viewer
```

---

## Bugs corrigés lors du déploiement

| Problème | Cause | Fix |
|---|---|---|
| `FastMCP.__init__() got unexpected keyword argument 'version'` | API MCP SDK v1.26 n'accepte pas `version` | Remplacé par `instructions` |
| `'function' object is not subscriptable` (`list[Epic]`) | Python 3.11 conflit entre `list` builtin et méthode `list()` | Ajout `from __future__ import annotations` dans les 6 services |
| `invalid image name "...:": could not parse reference` | `$COMMIT_SHA` non substitué dans Cloud Build | Remplacé par `$SHORT_SHA` (variable built-in) |

---

## Implémentations récentes

### JWT Bearer Authentication pour MCP (Février 2026)

**Contexte :** Le serveur MCP nécessite une authentification sécurisée pour les déploiements en production.

**Implémentation :**
- Middleware `AuthMiddleware` dans `mcp_server/server.py` validant les tokens JWT
- Fonction `verify_jwt_token()` dans `mcp_server/auth.py` pour validation
- Script `scripts/generate_mcp_token.py` pour génération de tokens avec rôles
- Configuration MCP client avec header `Authorization: Bearer <token>`

**Rôles et permissions :**
- **Admin** : CRUD complet sur toutes les ressources
- **Contributor** : Lecture + création/mise à jour des stories et commentaires  
- **Viewer** : Lecture seule

**Fichiers modifiés :**
- `mcp_server/server.py` : Ajout du middleware d'authentification
- `mcp_server/auth.py` : Création du module d'authentification
- `scripts/generate_mcp_token.py` : Utilitaire de génération de tokens
- `.vscode/mcp.json` : Configuration avec Bearer token
- `documentation/MCP_AUTH_GUIDE.md` : Guide complet d'authentification

**Variable d'environnement :**
- `MCP_DISABLE_AUTH=true` : Désactive l'auth en développement local (⚠️ JAMAIS en production)
