# Project File Tree

```
llm-task-manager/
├── README.md
├── ARCHITECTURE.md
├── pyproject.toml
├── .gitignore
├── .dockerignore
├── Dockerfile
├── cloudbuild.yaml
├── alembic/
│   ├── __init__.py
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── exceptions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── epic.py
│   │   ├── story.py
│   │   ├── sprint.py
│   │   ├── comment.py
│   │   └── document.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── epic.py
│   │   ├── story.py
│   │   ├── sprint.py
│   │   ├── comment.py
│   │   └── document.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   ├── health.py
│   │   ├── projects.py
│   │   ├── epics.py
│   │   ├── stories.py
│   │   ├── sprints.py
│   │   ├── comments.py
│   │   └── documents.py
│   └── services/
│       ├── __init__.py
│       ├── project_service.py
│       ├── epic_service.py
│       ├── story_service.py
│       ├── sprint_service.py
│       ├── comment_service.py
│       └── document_service.py
├── mcp_server/
│   ├── __init__.py
│   ├── server.py
│   ├── shared_services.py
│   └── tools/
│       ├── __init__.py
│       ├── project_tools.py
│       ├── epic_tools.py
│       ├── story_tools.py
│       ├── sprint_tools.py
│       ├── comment_tools.py
│       └── document_tools.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_schemas.py
│   │   ├── test_services.py
│   │   └── test_business_rules.py
│   └── integration/
│       ├── test_api_crud.py
│       ├── test_story_workflow.py
│       └── test_mcp_tools.py
├── scripts/
│   ├── seed_templates.py
│   └── init_db.py
└── sql/
    ├── schema.sql
    └── seed_data.sql
```