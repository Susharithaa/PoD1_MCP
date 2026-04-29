# MCP Hub

An AI-powered platform that parses API documentation (PDFs, OpenAPI specs, Postman collections) and registers them as MCP tools, enabling ChatGPT and other LLM clients to discover and call your APIs.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [First-Time Admin Registration](#first-time-admin-registration)
6. [Logging In (OTP Flow)](#logging-in-otp-flow)
7. [Admin Responsibilities](#admin-responsibilities)
8. [Running Tests](#running-tests)
9. [Environment Variables Reference](#environment-variables-reference)
10. [Production Setup (PostgreSQL)](#production-setup-postgresql)
11. [Common Issues](#common-issues)

---

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| npm | 9+ | Comes with Node.js |
| Git | any | https://git-scm.com |

Optional (for real AI parsing):
- **OpenAI API key** — get one at https://platform.openai.com/api-keys
- **Gmail App Password** — for OTP login emails (see [SMTP Setup](#smtp-gmail-setup))

---

## Project Structure

```
mcp_hub/
├── backend/          # FastAPI server
│   ├── agents/       # 8-agent AI pipeline
│   ├── models/       # SQLAlchemy ORM models
│   ├── routers/      # API route handlers
│   ├── utils/        # Auth, encryption, OTP, etc.
│   ├── main.py       # App entry point
│   ├── config.py     # Settings (reads .env)
│   ├── requirements.txt
│   └── .env          # You create this (see below)
├── frontend/         # React + Vite SPA
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Backend Setup

### 1. Navigate to the backend folder

```bash
cd backend
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your `.env` file

Copy the example and fill in your values:

```bash
# Windows
copy .env.Example .env

# macOS / Linux
cp .env.Example .env
```

Then open `.env` and set at minimum:

```env
# ── Required ──────────────────────────────────────────────────────────────────

# OpenAI API key — set to "mock" to run without calling OpenAI (dev/demo mode)
OPENAI_API_KEY=sk-...

# Set true to skip all real LLM calls (fast local testing, no API key needed)
MOCK_LLM=false

# Secret key for JWT tokens — change this to any long random string
JWT_SECRET=change-me-to-a-long-random-string

# Credential encryption key — generate with:
#   python -c "import secrets; print(secrets.token_hex(32))"
ENCRYPTION_KEY=your-generated-hex-key

# ── SMTP (required for OTP login emails) ──────────────────────────────────────
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-gmail-app-password

# ── Optional — leave blank to skip ────────────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

> **Running without OpenAI / SMTP?** Set `MOCK_LLM=true` and configure SMTP so OTP emails are delivered. See [Common Issues](#common-issues) for the dev workaround if you cannot configure SMTP.

### 5. SMTP (Gmail) Setup

MCP Hub uses email OTP for login. You need a Gmail App Password (not your regular Gmail password).

1. Enable 2-Step Verification on your Google account: https://myaccount.google.com/security
2. Go to **App Passwords**: https://myaccount.google.com/apppasswords
3. Select **Mail** → **Other** → name it "MCP Hub" → click **Generate**
4. Copy the 16-character password into `.env` as `SMTP_PASSWORD`
5. Set `SMTP_USER` to your full Gmail address

### 6. Start the backend server

```bash
# Development (auto-reload on file changes)
uvicorn main:app --reload

# Production / network-accessible
uvicorn main:app --host 0.0.0.0 --port 8000
```

The backend runs at **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

---

## Frontend Setup

Open a **new terminal** (keep the backend running).

### 1. Navigate to the frontend folder

```bash
cd frontend
```

### 2. Install dependencies

```bash
npm install
```

### 3. Start the dev server

```bash
npm run dev
```

The frontend runs at **http://localhost:5173**

---

## First-Time Admin Registration

The **very first user** to register on a fresh database is automatically granted the `admin` role. All subsequent registrations are `user` role by default.

### Steps

1. Open **http://localhost:5173/register**
2. Enter your email, full name, and a password
3. Click **Register** — you are now the admin
4. An OTP code is sent to your email
5. Enter the 6-digit code on the verification screen
6. You are logged in as **admin**

> **Important:** Do this before sharing the app with anyone else. Whoever registers first owns admin access.

---

## Logging In (OTP Flow)

Every login requires a one-time password sent by email. The flow is:

```
Enter email + password  →  OTP sent to email  →  Enter 6-digit code  →  Logged in
```

1. Go to **http://localhost:5173/login**
2. Enter your email and password → click **Sign In**
3. Check your inbox for an email from MCP Hub (subject: *"Your MCP Hub verification code"*)
4. Enter the 6-digit code within **10 minutes**
5. Done — you are logged in with a 7-day session token

### Social Login (Google / GitHub)

If you configured OAuth credentials in `.env`, users can also sign in with Google or GitHub buttons on the login page. The first social login creates a new account (with `user` role unless it is the very first account overall).

---

## Admin Responsibilities

After logging in as admin, you can manage the platform from the **Admin** panel (shield icon in the sidebar):

### Manage Users

- **View all users** — see roles, status, and credits
- **Change role** — promote a user to `admin` or demote to `user`
- **Activate / Deactivate** — block a user from logging in

### Approve Chat Access

Regular users must request access before they can use the AI chat features. As admin:

1. Go to the **Admin** panel
2. Users who clicked "Request Access" appear with status `pending`
3. Click **Approve** to grant access or **Reject** to deny
4. Optionally add credits to approved users for API usage billing

> **Tip:** The admin user automatically has `approved` chat status. New users start with `none` until they request and are approved.

---

## Running Tests

```bash
# From the backend/ directory with venv activated
cd backend
source venv/Scripts/activate   # Windows: venv\Scripts\activate

# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_confirm_redirect.py -v
python -m pytest tests/test_hitl_base_url.py -v
python -m pytest tests/test_patch_draft.py -v
```

Tests use an in-memory SQLite database and `MOCK_LLM=true` — no real API keys or database needed.

---

## Environment Variables Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | `mock` | Yes (for AI) | OpenAI key. Set to `mock` with `MOCK_LLM=true` for dev |
| `MOCK_LLM` | `false` | No | Skip OpenAI calls — useful for demos and testing |
| `DATABASE_URL` | `sqlite:///./mcp_hub.db` | No | SQLite (default) or PostgreSQL URL |
| `UPLOAD_DIR` | `./uploads` | No | Where uploaded docs are saved |
| `CORS_ORIGINS` | `http://localhost:5173` | No | Comma-separated allowed origins |
| `JWT_SECRET` | `change-me-in-production` | Yes | Secret for signing JWT tokens — must be changed |
| `JWT_EXPIRE_MINUTES` | `10080` (7 days) | No | Session token lifetime |
| `ENCRYPTION_KEY` | _(empty)_ | Yes | Hex key for encrypting stored API credentials |
| `SMTP_HOST` | `smtp.gmail.com` | No | SMTP server host |
| `SMTP_PORT` | `587` | No | SMTP port (TLS) |
| `SMTP_USER` | _(empty)_ | Yes | Gmail address for sending OTP emails |
| `SMTP_PASSWORD` | _(empty)_ | Yes | Gmail App Password (16 chars) |
| `GOOGLE_CLIENT_ID` | _(empty)_ | No | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | _(empty)_ | No | Google OAuth2 client secret |
| `GITHUB_CLIENT_ID` | _(empty)_ | No | GitHub OAuth2 client ID |
| `GITHUB_CLIENT_SECRET` | _(empty)_ | No | GitHub OAuth2 client secret |
| `FRONTEND_URL` | `http://localhost:5173` | No | Used for OAuth callback redirects |

---

## Production Setup (PostgreSQL)

For production, switch from SQLite to PostgreSQL:

### 1. Create a PostgreSQL database

```sql
CREATE DATABASE mcp_hub;
CREATE USER mcp_user WITH PASSWORD 'strongpassword';
GRANT ALL PRIVILEGES ON DATABASE mcp_hub TO mcp_user;
```

### 2. Update `.env`

```env
DATABASE_URL=postgresql://mcp_user:strongpassword@localhost:5432/mcp_hub
```

### 3. Run Alembic migrations (if applicable)

```bash
alembic upgrade head
```

The app also auto-creates tables on startup via `init_db()` — safe to run on a fresh database.

### 4. Set production security values

```env
JWT_SECRET=<64-char random string>
ENCRYPTION_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
CORS_ORIGINS=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

---

## Common Issues

### "Failed to send OTP email" on login

**Cause:** SMTP credentials are missing or wrong.

**Fix:**
1. Check `SMTP_USER` and `SMTP_PASSWORD` in `.env`
2. Make sure you are using a Gmail **App Password**, not your regular Gmail password
3. Confirm 2-Step Verification is enabled on the Gmail account

**Dev workaround (no SMTP configured):** You can retrieve the OTP directly from the running backend logs. When `send_otp_email` fails, the error is logged — temporarily add a `print(code)` in `utils/otp.py → generate()` to print codes to the terminal during local development.

---

### "Session not found" after page refresh during upload

The background pipeline runs asynchronously. If you refresh while the pipeline is processing (`CLASSIFYING`, `PARSING`, etc.), the page will poll automatically until it reaches `HITL_PENDING`. Just wait — do not refresh again.

---

### Frontend shows blank page / Cannot connect

Make sure both servers are running:
- Backend on port **8000**: `uvicorn main:app --reload`
- Frontend on port **5173**: `npm run dev`

Then open **http://localhost:5173** (not port 8000).

---

### `ModuleNotFoundError: No module named 'sqlalchemy'`

The virtual environment is not activated.

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Then retry `uvicorn main:app --reload`.

---

### User cannot access Chat / gets "Access Required" banner

Regular users must request and receive admin approval before using AI chat:

1. User clicks **Request Access** in the app
2. Admin goes to **Admin panel → Subscription Requests**
3. Admin clicks **Approve**
4. Admin optionally adds credits via **Top Up**

---

### How to reset the database (local dev)

```bash
# Stop the server, then:
rm backend/mcp_hub.db

# Restart — tables are recreated automatically
uvicorn main:app --reload
```

The first user to register after reset becomes admin again.
