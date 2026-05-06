# AGENTS.md

Guidance for AI coding agents and developers working in this repository.

## Project Overview

MCP Hub is a FastAPI + React/Vite application for turning API documentation or manual API definitions into registered MCP-style tools. Users can register/login, upload or describe APIs, review human-in-the-loop generated schemas, save endpoints to the registry, connect tools to ChatGPT-style chat, and execute registered APIs through a guarded tool orchestrator.

The backend is a modular monolith: auth, subscriptions, agent sessions, registry CRUD, monitoring, admin operations, domain demo APIs, MCP endpoints, and ChatGPT tool execution all run in one FastAPI app.

## Repository Layout

- `backend/` - FastAPI app, SQLAlchemy models, routers, schemas, LLM/agent pipeline, tool orchestration, utilities, Alembic migrations, and tests.
- `backend/agents/` - API creation pipeline: classify, parse, generate schema, reconcile, score confidence, validate, live-test, and save.
- `backend/orchestrator/tool_orchestrator.py` - Runtime HTTP execution for LLM tool calls, including parameter validation, dry-run/emergency-stop checks, SSRF validation, auth injection, timeout, and masking.
- `backend/routers/` - API route modules mounted by `backend/main.py`.
- `backend/utils/` - Auth, encryption, masking, safety controls, SSRF protection, migrations, observability, endpoint validation, document extraction, and email/OTP helpers.
- `backend/alembic/` - Database migrations. Startup also runs compatibility migrations through `utils/migrations.py` and `database._migrate()`.
- `frontend/` - React 18 + Vite + Tailwind SPA.
- `frontend/src/lib/api.js` - Central Axios client and frontend API wrapper.
- `frontend/src/pages/` - Route-level UI pages.
- `frontend/src/context/` - Auth, theme, language, and upload state.
- `docs/` - Architecture, flow, product docs, generated diagrams, and images.
- `testing/` - Sample API documents/specs for parser and upload testing.
- `Reports/` and root `*.xlsx` / XML files - Test/report artifacts; avoid touching unless the task is report-related.
- `run.py` - Convenience backend runner from repository root.

## Local Setup

Backend from repository root:

```bash
python -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
python run.py
```

Alternative backend command from `backend/`:

```bash
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

## Environment And Configuration

- `backend/config.py` loads `backend/.env` by file location, then the active profile file for `APP_ENV`, then any existing fallback profile files.
- Supported example files are `backend/.env.example`, `backend/.env.dev.example`, `backend/.env.stg.example`, and `backend/.env.prod.example`.
- Local SQLite is the default: `DATABASE_URL=sqlite:///./mcp_hub.db`.
- `MCP_HUB_CONTAINER` switches the default SQLite path into `DATA_DIR`.
- `CORS_ORIGINS` is comma-separated and defaults to `http://localhost:5173`.
- `UPLOAD_DIR` defaults to `./uploads` relative to the backend process.

For local no-key LLM testing:

```env
OPENAI_API_KEY=mock
MOCK_LLM=true
```

For real OpenAI calls:

```env
OPENAI_API_KEY=<real key>
MOCK_LLM=false
```

Azure OpenAI is also supported through:

```env
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=
```

Security-related settings currently used by the code include:

- `JWT_SECRET`
- `ENCRYPTION_KEY`
- `ALLOW_PRIVATE_TOOL_HOSTS`
- `ALLOW_INSECURE_SSL`
- `EMERGENCY_STOP`
- `DRY_RUN_TOOLS`
- `MAX_TOOL_EXECUTION_MS`
- `READ_ONLY_MODE`
- `MAX_REQUEST_BYTES`
- `ADMIN_BOOTSTRAP_EMAILS`
- `OTEL_ENABLED`

SMTP placeholders can trigger the local development OTP path in `backend/utils/email_sender.py`; when that happens, the backend logs the OTP as `[DEV OTP]`.

## Secrets And Ignored Files

Never commit secrets or generated local state.

Keep these untracked:

- `backend/.env`
- profile-local env files such as `backend/.env.dev`, `backend/.env.stg`, `backend/.env.prod`
- `backend/venv/`, `.venv/`, and other virtualenv folders
- `frontend/node_modules/`
- `frontend/dist/`
- `mcp_hub.db`, `*.sqlite`, `*.sqlite3`
- `uploads/` and `backend/uploads/*` except `.gitkeep`
- `_gitmeta/` and `_gitmeta_test/`
- caches such as `__pycache__/`, `.pytest_cache/`, `.vite/`
- logs and local editor/OS files

Before committing, run:

```bash
git status --short
git ls-files | rg '(^|/)\.env$|venv|node_modules|mcp_hub\.db|^uploads/|backend/uploads|_gitmeta|frontend/dist'
git grep -n -I 'sk-proj-\|sk-[A-Za-z0-9]' HEAD
```

## Running Tests And Checks

Backend tests:

```bash
cd backend
source venv/bin/activate
python -m pytest tests -v
```

Targeted backend test:

```bash
cd backend
python -m pytest tests/test_tool_orchestrator.py -v
```

Frontend build:

```bash
cd frontend
npm run build
```

There is no frontend test script in `frontend/package.json` at the time of writing.

## Runtime Architecture Notes

- `backend/main.py` creates the FastAPI app, configures CORS, request context middleware, rate-limit handling, OpenTelemetry setup, static serving for `testing/`, and all routers.
- Startup runs logging setup, server migrations, and `init_db()`.
- `backend/database.py` creates the SQLAlchemy engine and still contains defensive column-add migrations for older SQLite databases.
- `backend/llm/client.py` uses `gpt-4o` for OpenAI calls and falls back to deterministic mock responses when `MOCK_LLM=true` or the key is missing/placeholder-like.
- `backend/agents/orchestrator.py` owns the session state machine:
  `INIT -> CLASSIFYING -> PARSING -> SCHEMA_GENERATING -> RECONCILING -> CONFIDENCE_SCORING -> HITL_PENDING -> VALIDATING -> API_TESTING -> SAVING -> SAVED`.
- Validation failures or blocking API-test verdicts return the session to `HITL_PENDING`.
- Manual API creation uses `/api/agent/manual`, creates a draft directly, and skips LLM review.
- Credentials stored on endpoints or sessions should pass through `utils/encryption.py` and be masked before logging or returning diagnostic text.
- Outbound tool execution should continue to use `utils/ssrf.py`, `utils/safety.py`, and `utils/masking.py`; do not bypass those helpers.

## Frontend Notes

- The frontend API base URL is currently hard-coded in `frontend/src/lib/api.js` as `http://localhost:8000`.
- Auth tokens are stored in `localStorage` under `mcp_token` and added as Bearer tokens by the Axios interceptor.
- A 401 response clears the token and redirects to `/login`.
- The app shell in `frontend/src/App.jsx` provides sidebar navigation, topbar controls, theme/language/upload providers, and protected app layout.
- Keep frontend changes consistent with the existing Tailwind utility style and context/provider pattern.

## Useful Test Upload Files

- `testing/sample_weather_api.yaml` - Small fake weather OpenAPI spec; `api.example.com` reachability failures are expected.
- `testing/sample_local_weather.yaml` - Local/weather-style sample.
- `testing/sample_books_api.json` - Small OpenAPI JSON spec.
- `testing/sample_plain_api.txt` - Plain text API description.
- `testing/Swagger_test.json` - Swagger/OpenAPI parser sample.
- `testing/Mixed_doc.txt` - Mixed text document sample.
- `testing/yahoo_search_serpapi.yaml` - Yahoo Search through SerpApi; requires a SerpApi key configured as API key query parameter auth.

For no-key live API testing, prefer a public API that does not require authentication, such as Open-Meteo.

## Development Guidelines

- Keep changes scoped and follow existing module boundaries.
- Prefer existing routers, schemas, models, context providers, and utility helpers over adding parallel patterns.
- Add or update tests when behavior changes, especially for auth, registry persistence, the agent state machine, tool execution, masking, SSRF, and migrations.
- Do not log credentials, OTP values except the deliberate dev fallback, access tokens, API keys, or decrypted endpoint auth.
- Be careful when changing startup migrations; local SQLite databases may depend on compatibility paths in both Alembic and `database._migrate()`.
- Use structured JSON parsing/serialization for schemas and API definitions. Avoid ad hoc string manipulation for OpenAPI, tool schema, or credentials data.
- Check `README.md` before relying on it; it currently contains merge-conflict markers and may be stale.

## Git Notes

Current remote:

```text
origin https://github.com/Susharithaa/PoD1_MCP.git
```

Current working branch observed in this workspace:

```text
Dev
```

This workspace may use separate Git metadata directories in some environments. Treat `_gitmeta/` and `_gitmeta_test/` as local-only metadata and never commit them.
