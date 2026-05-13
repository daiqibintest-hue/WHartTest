# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WHartTest is an AI-driven intelligent test case generation platform. Monorepo with 6 sub-projects:

- `WHartTest_Django/` — Django 5.2 + DRF + Celery + LangChain/LangGraph backend
- `WHartTest_Vue/` — Vue 3 + TypeScript + Vite + Arco Design Vue frontend
- `WHartTest_Actuator/` — Python + Playwright UI automation executor
- `WHartTest_MCP/` — Python FastMCP tool service
- `WHartTest_Skills/` — Agent skill bundles
- `WHartTest_WeixinPluginHost/` — WeChat integration (Node.js)

## Common Commands

### Backend
```bash
cd WHartTest_Django
uv run python manage.py runserver                     # Dev server (port 8000)
uv run python manage.py makemigrations                # Generate migrations
uv run python manage.py migrate                       # Apply migrations
uv run celery -A wharttest_django worker --loglevel=info -Q celery,task_center -B
```

### Frontend
```bash
cd WHartTest_Vue
npm run dev          # Vite dev server, proxies /api to localhost:8000
npm run build        # vue-tsc -b && vite build
```

### Docker (production-like)
```bash
docker-compose up -d                              # All 9 services
docker exec wharttest-backend python manage.py migrate   # Run migration in container
docker cp <local-file> wharttest-backend:/app/<path>     # Copy files to backend container
docker cp WHartTest_Vue/dist/. wharttest-frontend:/usr/share/nginx/html/  # Deploy frontend
```

## Architecture

### Services (Docker)

| Service | Port | Role |
|---------|------|------|
| backend | 8912 | Django API (uvicorn + Celery worker + beat via supervisord) |
| frontend | 8913 | Vue SPA (nginx) |
| postgres | 8919 | Primary database |
| redis | 8911 | Celery broker + cache |
| qdrant | 8918 | Vector database |
| xinference | 8917 | Local LLM inference |
| mcp | 8914/8915 | MCP tool service |
| playwright-mcp | 8916 | Playwright MCP |

Default login: `http://localhost:8913` admin/admin123456

### Backend (WHartTest_Django)

- **Config**: `wharttest_django/` package (settings.py, urls.py, celery.py, asgi.py)
- **Base ViewSet**: `wharttest_django.viewsets.BaseModelViewSet` (IsAuthenticated + HasModelPermission)
- **Routing**: `DefaultRouter` for top-level, `NestedSimpleRouter` for project-scoped resources. All under `/api/`
- **Auth**: JWT (Bearer token) + API Key
- **Response format**: Auto-wrapped by `UnifiedResponseRenderer` — don't manually construct `{"status", "code", "message", "data"}` in views
- **Celery**: Redis broker, `django_celery_beat.schedulers:DatabaseScheduler`, tasks in `task_center` queue use `@shared_task(queue='task_center')`
- **Package manager**: `uv` (all Python commands use `uv run`)
- **Timezone**: Asia/Shanghai

15 Django apps: `accounts`, `projects`, `testcases`, `knowledge`, `langgraph_integration`, `mcp_tools`, `api_keys`, `prompts`, `requirements`, `orchestrator_integration`, `skills`, `testcase_templates`, `ui_automation`, `weixin_integration`, `task_center`

### Knowledge Base (knowledge/)

The `knowledge` app is the most complex module. Key files:

- `models.py` — `KnowledgeGlobalConfig` (singleton), `KnowledgeBase`, `Document`, `DocumentChunk`, `QueryLog`
- `services.py` — Core RAG pipeline:
  - `VectorStoreManager` — Qdrant operations, hybrid search (Dense + BM25 sparse + RRF fusion + Reranker + MMR)
  - `KnowledgeBaseService` — Document processing, query rewrite, multi-query, HyDE, parent-child expansion
  - Collection naming: `kb_{knowledge_base_id}`
- `views.py` — ViewSet with `query` action for RAG retrieval

Retrieval pipeline: original query → HyDE hypothetical answer → Multi-Query/Query Rewrite variants → per-variant search → merge+dedup → parent-child/neighbor expansion → return

### Frontend (WHartTest_Vue)

- **UI**: Arco Design Vue (`@arco-design/web-vue`)
- **State**: Pinia stores in `src/store/` (authStore, projectStore, themeStore)
- **HTTP**: Axios in `src/utils/request.ts` (JWT auto-refresh interceptor, response unwrapped automatically)
- **Features**: `src/features/<module>/` each with `api/`, `components/`, `types/`, `views/`
- **Routing**: Vue Router 4, `meta: { requiresAuth: true }` for protected pages

## Coding Conventions

- Vue: `<script setup lang="ts">`, PascalCase components, prefer `interface` over `type`
- Python: PEP 8, model fields use `gettext_lazy as _` for i18n
- Migration naming: `NNNN_descriptive_name.py`
- Single file max ~500 lines; split if larger
- API calls in frontend: `response.data` is already unwrapped by Axios interceptor
- Arco Design `<a-select>` in scrollable modals: use `:popup-container` to control dropdown positioning
