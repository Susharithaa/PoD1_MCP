# AGENTS.md

Guidance for AI coding agents and developers working in this repository.

## Project Overview

MCP Hub is a FastAPI + React/Vite application that parses API documentation and registers endpoints as MCP-style tools. Users can upload OpenAPI, Swagger, JSON, text, Markdown, or PDF API descriptions, review the generated schema, save tools, and chat with connected tools through the ChatGPT integration.

## Repository Layout

- `backend/` - FastAPI app, SQLAlchemy models, routers, agents, utilities, Alembic migrations, and tests.
- `frontend/` - React + Vite single-page app.
- `Docs/` - Architecture, product, flow, and diagram documentation.
- `testing/` - Sample API documents for upload/parser testing.
- `run.py` - Convenience backend runner from the repository root.

## Local Setup

Backend:

```powershell
cd D:\SoftBank\POD1\Agents\MCP\mcp_hub-3-api-accuracy-improvements
python -m venv backend\venv
backend\venv\Scripts\activate
pip install -r backend\requirements.txt
copy backend\.env.example backend\.env
python run.py
```

Frontend:

```powershell
cd D:\SoftBank\POD1\Agents\MCP\mcp_hub-3-api-accuracy-improvements\frontend
npm install
npm run dev
```

Default URLs:

- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

## Environment And Secrets

- Never commit `backend/.env`.
- Use `backend/.env.example` for placeholder configuration.
- Rotate any key that was pasted into logs, chat, screenshots, or terminal output.
- `backend/config.py` intentionally loads `backend/.env` by file location so `python run.py` works from the repo root.
- For local no-key testing, use:

```env
OPENAI_API_KEY=mock
MOCK_LLM=true
```

- For real GPT calls, use:

```env
OPENAI_API_KEY=<real key>
MOCK_LLM=false
```

- SMTP placeholders trigger a local dev OTP fallback in `backend/utils/email_sender.py`; the OTP prints in the backend terminal as `[DEV OTP]`.

## Ignored Local Files

The following must remain untracked:

- `backend/.env`
- `backend/venv/`
- `frontend/node_modules/`
- `mcp_hub.db`
- `uploads/`
- `backend/uploads/*` except `.gitkeep`
- `_gitmeta/` and `_gitmeta_test/`

Before committing, verify:

```powershell
git status --short
git ls-files | Select-String -Pattern "(^|/)\.env$|venv|node_modules|mcp_hub\.db|^uploads/|_gitmeta"
git grep -n -I "sk-proj-" HEAD
```

## Running Tests

Backend tests:

```powershell
cd backend
venv\Scripts\activate
python -m pytest tests -v
```

Frontend build:

```powershell
cd frontend
npm run build
```

## Useful Test Upload Files

- `testing/sample_weather_api.yaml` - Small fake weather OpenAPI spec for parser flow testing.
- `testing/sample_books_api.json` - Small OpenAPI JSON spec.
- `testing/sample_plain_api.txt` - Plain text API description.
- `testing/yahoo_search_serpapi.yaml` - Yahoo Search through SerpApi. Requires a SerpApi key configured as API key query parameter auth.

For no-key live API testing, prefer creating or using a public API spec that does not require authentication, such as Open-Meteo.

## Development Notes

- Keep changes scoped and follow existing patterns.
- Do not commit generated caches, local databases, uploaded user files, or dependency directories.
- Be careful with auth credentials stored on endpoints; values should be encrypted by backend utilities and never logged.
- The ChatGPT integration can run in mock mode without OpenAI, but it will not perform real LLM reasoning or live tool calling.
- The sample weather spec uses `https://api.example.com`, so endpoint reachability checks are expected to fail unless replaced with a real API.

## Git Notes

This workspace may use a separate Git metadata directory because Windows ACLs blocked a normal `.git` directory during initialization. Treat `_gitmeta/` as local-only metadata and never commit it.

Current remote:

```text
origin https://github.com/Susharithaa/POD1-PoC.git
```

Main working branch for this project:

```text
MCP
```
