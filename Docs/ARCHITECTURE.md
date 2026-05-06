# MCP Hub — System & Architecture Design

---

## 1. System Overview

MCP Hub is a centralized API ecosystem platform that lets users define, publish, discover, and attach APIs to LLMs (initially ChatGPT). It abstracts away auth complexity, schema formatting, and execution routing behind a clean hub interface.

```
┌───────────────────────────────────────────────────────────────────┐
│                          MCP Hub Platform                         │
│                                                                   │
│   ┌──────────┐   ┌────────────┐   ┌─────────────┐   ┌────────┐  │
│   │  Portal  │   │  API       │   │  Execution  │   │  MCP   │  │
│   │  (Web)   │──▶│  Registry  │──▶│  Engine     │──▶│ Bridge │  │
│   └──────────┘   └────────────┘   └─────────────┘   └────────┘  │
│         │              │                 │                         │
│         ▼              ▼                 ▼                         │
│   ┌──────────┐   ┌────────────┐   ┌─────────────┐               │
│   │  AI      │   │  Schema    │   │  Auth       │               │
│   │  Assist  │   │  Translator│   │  Vault      │               │
│   └──────────┘   └────────────┘   └─────────────┘               │
└───────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       ┌─────────────┐               ┌───────────────┐
       │  ChatGPT /  │               │  3rd-party    │
       │  LLM clients│               │  APIs         │
       └─────────────┘               └───────────────┘
```

---

## 2. High-Level Architecture

### 2.1 Current Logical Deployment Architecture

```
┌────────────────────┐       ┌──────────────────────────────┐
│ React/Vite Portal  │──────▶│ FastAPI Backend              │
│ Static SPA         │       │ - Auth + OTP/OAuth           │
└────────────────────┘       │ - Agent API creation flow    │
                             │ - Registry CRUD              │
                             │ - ChatGPT/MCP integration    │
                             │ - Tool execution proxy       │
                             │ - Admin/monitoring APIs      │
                             └──────────────┬───────────────┘
                                            │
                 ┌──────────────────────────┼──────────────────────────┐
                 ▼                          ▼                          ▼
        ┌────────────────┐        ┌──────────────────┐       ┌─────────────────┐
        │ PostgreSQL     │        │ Blob/File Store  │       │ OpenAI or       │
        │ or local SQLite│        │ Uploads/docs     │       │ Azure OpenAI    │
        └────────────────┘        └──────────────────┘       └─────────────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │ Third-party APIs │
                                  │ called by tools  │
                                  └──────────────────┘
```

The checked-in code is currently a modular monolith. The frontend is a React/Vite SPA, and the backend is a single FastAPI application with SQLAlchemy models, routers, the agent pipeline, and runtime tool execution in one deployable service.

### 2.2 Required Azure Target Architecture

For an Azure deployment, use managed PaaS services first. The application does not currently require Kubernetes or a split microservice deployment.

```
Users / Admins
      │
      ▼
┌──────────────────────────────┐
│ Azure Front Door + WAF        │
│ TLS, global entry, WAF rules  │
└───────────────┬──────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌────────────────┐  ┌────────────────────────────┐
│ Static Web App │  │ Azure Container Apps        │
│ React/Vite SPA │  │ FastAPI backend container   │
└────────────────┘  │ uvicorn/gunicorn workers    │
                    └──────────────┬─────────────┘
                                   │ Managed Identity
          ┌────────────────────────┼─────────────────────────┐
          ▼                        ▼                         ▼
┌──────────────────┐     ┌──────────────────┐      ┌──────────────────┐
│ Azure Database   │     │ Azure Key Vault  │      │ Azure Blob       │
│ for PostgreSQL   │     │ secrets/keys     │      │ uploads/docs     │
│ Flexible Server  │     └──────────────────┘      └──────────────────┘
└──────────────────┘
          │                        │                         │
          └──────────────┬─────────┴──────────────┬──────────┘
                         ▼                        ▼
               ┌──────────────────┐     ┌────────────────────┐
               │ Azure OpenAI     │     │ App Insights /     │
               │ or OpenAI API    │     │ Log Analytics      │
               └──────────────────┘     └────────────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │ Third-party APIs │
               │ via controlled   │
               │ outbound egress  │
               └──────────────────┘
```

#### Azure services needed

| Need | Azure service | Why it is needed |
|---|---|---|
| SPA hosting | Azure Static Web Apps or Azure Storage Static Website + CDN | Hosts the built `frontend/dist` assets. Static Web Apps is simpler for app routing and TLS. |
| API runtime | Azure Container Apps | Runs the FastAPI backend container with autoscaling and managed identity without AKS overhead. |
| Container images | Azure Container Registry | Stores backend container images for Container Apps deployments. |
| Database | Azure Database for PostgreSQL Flexible Server | Production replacement for local SQLite; supports relational registry/session/auth data. |
| Uploaded documents | Azure Blob Storage | Durable storage for uploaded API docs instead of local `./uploads`. |
| Secrets | Azure Key Vault | Stores JWT secret, encryption key, SMTP credentials, OAuth secrets, OpenAI/Azure OpenAI keys, and future endpoint credential roots. |
| LLM | Azure OpenAI Service, with OpenAI API as fallback | The code already has Azure OpenAI settings and OpenAI mock mode for local testing. |
| Edge and security | Azure Front Door with WAF | Public TLS endpoint, WAF protection, routing to SPA/API, and optional global acceleration. |
| Observability | Application Insights + Log Analytics | Receives OpenTelemetry traces, app logs, request metrics, and operational dashboards. |
| Networking | VNet integration, Private Endpoints, NAT Gateway or Azure Firewall | Keeps database, storage, Key Vault, and Azure OpenAI private where possible and gives tool execution controlled egress. |
| CI/CD | GitHub Actions or Azure DevOps | Builds frontend, builds/pushes backend image, applies migrations, deploys infrastructure and app versions. |

#### Minimum production resource groups

- `rg-mcp-hub-network` - VNet, private DNS zones, NAT/Firewall, Front Door profile if managed centrally.
- `rg-mcp-hub-app-prod` - Static Web App, Container App Environment, backend Container App, ACR, managed identities.
- `rg-mcp-hub-data-prod` - PostgreSQL Flexible Server, Blob Storage account, Key Vault.
- `rg-mcp-hub-observability-prod` - Log Analytics workspace, Application Insights, alerts and dashboards.

For a proof of concept, these can be collapsed into one resource group. For production, keep app, data, and network concerns separate to simplify RBAC and lifecycle management.

#### Azure network flow

1. Browser loads the React SPA from Azure Static Web Apps through Azure Front Door.
2. SPA calls the FastAPI backend at `/api/*` through Front Door or directly through the Container App ingress.
3. Container Apps uses managed identity to read Key Vault secrets and connect to Azure resources.
4. Backend reads/writes registry, users, sessions, audit, and usage data in Azure Database for PostgreSQL.
5. Backend stores uploaded documents in Blob Storage. Local `UPLOAD_DIR=./uploads` is acceptable only for local development.
6. Agent pipeline calls Azure OpenAI or OpenAI based on environment settings.
7. Tool execution calls registered third-party APIs through controlled outbound egress. Keep SSRF protections enabled and consider domain allowlists for production.
8. Logs, traces, metrics, and failures flow into Application Insights and Log Analytics.

#### Production configuration mapping

| Current setting | Azure production value |
|---|---|
| `APP_ENV` | `prod` |
| `DATABASE_URL` | PostgreSQL connection string from Azure Database for PostgreSQL, preferably injected from Key Vault. |
| `UPLOAD_DIR` | Replace local path usage with Blob Storage-backed upload implementation before production scale. |
| `CORS_ORIGINS` | Static Web App / Front Door production URL. |
| `JWT_SECRET` | Key Vault secret. |
| `ENCRYPTION_KEY` | Key Vault secret; rotate through a planned credential migration process. |
| `AZURE_OPENAI_API_KEY` | Key Vault secret, or use managed identity if the client implementation is upgraded. |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint. |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name for the selected chat model. |
| `SMTP_USER`, `SMTP_PASSWORD` | Key Vault secrets, or replace with Azure Communication Services Email. |
| `OTEL_ENABLED` | `true` with Application Insights exporter configuration. |
| `ALLOW_PRIVATE_TOOL_HOSTS` | `false` for internet-facing production. |
| `ALLOW_INSECURE_SSL` | `false` for all shared environments. |
| `EMERGENCY_STOP` | Operational kill switch, controlled by admin process. |
| `DRY_RUN_TOOLS` | `false` in production; `true` in demos where live external calls are not allowed. |

#### Azure deployment phases

| Phase | Azure architecture | Scope |
|---|---|---|
| PoC | Static Web Apps + Container Apps + local/dev SQLite or small PostgreSQL + Key Vault | Prove frontend/backend flow, auth, upload, mock LLM, and registry. |
| Pilot | Container Apps + PostgreSQL Flexible Server + Blob Storage + Azure OpenAI + Application Insights | Production-like data durability, real LLM calls, upload persistence, observability. |
| Production | Front Door WAF + private endpoints + NAT/Firewall + autoscaling + backup/restore + CI/CD gates | Security hardening, controlled egress, HA, backups, alerts, release governance. |
| Enterprise | Multi-region Front Door, zone-redundant PostgreSQL, read replica, Azure API Management, Microsoft Entra ID SSO | Higher availability, enterprise auth, formal API gateway policies, tenant controls. |

### 2.3 Service Decomposition (Modular Monolith → Microservices)

Start as a **modular monolith** in Phase 1–2, extract to microservices in Phase 3–4.

| Module | Responsibility | Phase Extracted |
|---|---|---|
| `registry` | CRUD for API definitions | Monolith |
| `schema` | Schema validation, translation, AI suggestions | Monolith → Phase 2 |
| `execution` | Proxy requests to real APIs through guarded outbound egress | Phase 2 |
| `auth-vault` | Store and inject credentials through encrypted storage and Key Vault-backed roots | Phase 3 |
| `ai-assist` | LLM-powered schema/description generation with OpenAI or Azure OpenAI | Phase 2 |
| `marketplace` | Discovery, search, ratings | Phase 3 |
| `analytics` | Usage tracking, metrics | Phase 3 |
| `mcp-bridge` | MCP protocol adapter for LLM clients | Phase 1 |

---

## 3. Core Component Design

### 3.1 API Registry

Central store for all API definitions.

```
ApiDefinition
├── id (UUID)
├── workspace_id
├── name
├── description
├── visibility: PRIVATE | TEAM | PUBLIC
├── endpoints[]
│   ├── id
│   ├── path
│   ├── method: GET | POST | PUT | DELETE | PATCH
│   ├── headers: { key: string, value: string, secret: boolean }[]
│   ├── auth_config_id → AuthConfig
│   ├── input_schema: JSONSchema
│   └── output_schema: JSONSchema
├── tags[]
├── version (semver)
├── published_at
└── created_by
```

**Design Decisions:**
- Schemas stored as JSON columns in Postgres (JSONB).
- Versioning via immutable snapshots; consumers pin to a version.
- Soft-delete with `archived_at` to preserve history.

---

### 3.2 Schema Translator

Converts API definitions to LLM-consumable tool schemas.

```
Input:  ApiDefinition (internal format)
        │
        ▼
┌─────────────────────────────┐
│       Schema Translator     │
│                             │
│  1. Validate JSONSchema     │
│  2. Flatten nested objects  │
│  3. Generate descriptions   │
│  4. Map to target format    │
└──────────────┬──────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
  OpenAI Tools      MCP-style Tools
  Format            Internal Format
```

- Current implementation includes OpenAI tool translation in `backend/translators/openai_translator.py`
- Future adapters can be added for other MCP clients when needed
- Schema caching can be added with Azure Cache for Redis if registry read load requires it
- AI-assisted description enhancement via AI Assist Layer

---

### 3.3 Execution Engine

Proxies LLM tool-call requests to real APIs securely.

```
LLM Tool Call Request
        │
        ▼
┌─────────────────────────────────────────┐
│              Execution Engine           │
│                                         │
│  1. Validate tool call params           │
│     against input_schema                │
│                                         │
│  2. Resolve auth credentials            │
│     from Auth Vault                     │
│                                         │
│  3. Build outbound HTTP request         │
│     (inject headers, auth, body)        │
│                                         │
│  4. Execute with timeout + retry        │
│                                         │
│  5. Validate response against           │
│     output_schema                       │
│                                         │
│  6. Return normalized response          │
│     + emit execution event              │
└─────────────────────────────────────────┘
```

**Key constraints:**
- Current hard timeout: 5s per execution, additionally bounded by `MAX_TOOL_EXECUTION_MS`
- Current retry count: 0; retries can be enabled later once idempotency rules are explicit
- Execution logs stored for debugging (TTL: 30 days)
- Never log credential values; redact header values marked `secret: true`

---

### 3.4 Auth Vault

Secure credential storage and injection.

```
┌──────────────────────────────────────┐
│              Auth Vault              │
│                                      │
│  AuthConfig types:                   │
│  ├── API_KEY  (header/query)         │
│  ├── BEARER   (Authorization header) │
│  ├── BASIC    (username + password)  │
│  ├── OAUTH2   (client credentials)   │
│  └── CUSTOM   (arbitrary headers)    │
│                                      │
│  Storage: Azure Key Vault            │
│  plus encrypted DB values            │
│                                      │
│  Credentials never leave the vault   │
│  — only injected at execution time   │
└──────────────────────────────────────┘
```

- Credentials encrypted at rest (AES-256)
- Scoped per workspace; never cross-tenant accessible
- OAuth2 tokens auto-refreshed before expiry
- Audit log for every credential access

---

### 3.5 AI Assist Layer

LLM-powered features for schema generation and parameter mapping.

```
Capabilities:
├── Schema Suggestion
│   Input: user's API URL + sample response
│   Output: suggested JSONSchema for input/output
│
├── Description Generation
│   Input: endpoint path + method + schema
│   Output: human-readable description for LLM tool
│
├── Parameter Mapping
│   Input: natural language intent + available tool schemas
│   Output: tool name + parameter values
│
└── Error Explanation
    Input: HTTP error response
    Output: plain-English cause + fix suggestion
```

- Uses OpenAI-compatible chat calls; Azure OpenAI is supported through environment configuration
- Structured JSON outputs enforced through response format constraints where available
- Rate-limited per workspace to control costs

---

### 3.6 MCP Bridge

Adapter that exposes the MCP Hub as an MCP server to LLM clients.

```
LLM Client (ChatGPT / MCP client)
        │  MCP Protocol
        ▼
┌─────────────────────────────┐
│         MCP Bridge          │
│                             │
│  tools/list  ──▶ Registry   │
│  tools/call  ──▶ Execution  │
│                   Engine    │
│  resources/* ──▶ Registry   │
│                   (schemas) │
└─────────────────────────────┘
```

- Implements MCP spec (JSON-RPC 2.0 over HTTP/SSE)
- Auth: workspace API key in `Authorization: Bearer` header
- Dynamic tool list based on user's attached APIs
- Streams execution results via SSE for long-running calls

---

## 4. Data Model

```sql
-- Multi-tenancy
workspaces (id, name, plan, created_at)
workspace_members (workspace_id, user_id, role: OWNER|ADMIN|MEMBER)

-- API definitions
api_definitions (
  id, workspace_id, name, description,
  visibility, version, tags[],
  published_at, archived_at, created_by
)

api_endpoints (
  id, api_definition_id, name, description,
  path, method, headers JSONB,
  auth_config_id, input_schema JSONB,
  output_schema JSONB
)

-- Auth
auth_configs (
  id, workspace_id, name, type,
  secret_ref  -- pointer to Key Vault or encrypted credential reference, never raw value
)

-- Execution logs
execution_logs (
  id, workspace_id, api_endpoint_id,
  triggered_by,  -- user_id or mcp_session_id
  request_summary JSONB,  -- params only, no secrets
  response_status, response_summary JSONB,
  duration_ms, created_at
)
-- Partition by created_at, TTL index

-- Marketplace
api_reviews (id, api_definition_id, user_id, rating, comment, created_at)
api_installs (workspace_id, api_definition_id, installed_at)

-- Sessions (MCP)
mcp_sessions (
  id, workspace_id, llm_client,
  attached_api_ids UUID[],
  created_at, last_active_at
)
```

---

## 5. API Design (Internal REST)

### Core endpoints

```
POST   /workspaces/:id/apis              # Create API definition
GET    /workspaces/:id/apis              # List APIs
GET    /apis/:id                         # Get API detail
PUT    /apis/:id                         # Update API
DELETE /apis/:id                         # Archive API
POST   /apis/:id/publish                 # Publish (set visibility)

POST   /apis/:id/endpoints              # Add endpoint
PUT    /endpoints/:id                    # Update endpoint
POST   /endpoints/:id/test              # Test endpoint (proxied)

GET    /hub/apis                         # Browse public marketplace
GET    /hub/apis/:id                     # Public detail + schema
POST   /hub/apis/:id/install            # Install to workspace

POST   /mcp/sessions                     # Create MCP session
GET    /mcp/sessions/:id/tools          # List tools (MCP tools/list)
POST   /mcp/sessions/:id/execute        # Execute tool (MCP tools/call)

POST   /ai/suggest-schema               # AI schema suggestion
POST   /ai/generate-description         # AI description generation
```

### MCP Protocol Endpoints

```
GET    /mcp/:session_id                  # SSE connection (MCP transport)
POST   /mcp/:session_id                  # JSON-RPC request handler
```

---

## 6. Security Architecture

```
┌─────────────────────────────────────────────────┐
│                Security Layers                  │
│                                                 │
│  Layer 1: Transport                             │
│  └── TLS 1.3 everywhere                        │
│                                                 │
│  Layer 2: Auth & AuthZ                          │
│  ├── User Auth: OAuth2 (Google/GitHub SSO)      │
│  ├── Session: short-lived JWTs (15min)          │
│  ├── Refresh: rotating refresh tokens           │
│  └── API Access: workspace API keys (SHA-256)   │
│                                                 │
│  Layer 3: Multi-tenancy Isolation               │
│  └── workspace_id enforced on every DB query    │
│      (RLS policies in Postgres)                 │
│                                                 │
│  Layer 4: Credential Security                   │
│  ├── Secrets stored in Azure Key Vault          │
│  ├── Never logged or returned in responses      │
│  └── Audit trail on every access               │
│                                                 │
│  Layer 5: Execution Security                    │
│  ├── SSRF protection: block private IP ranges   │
│  ├── Request size limits (1MB body max)         │
│  ├── Allowlist for outbound domains (optional)  │
│  └── Rate limiting per workspace                │
└─────────────────────────────────────────────────┘
```

---

## 7. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | React 18 + Vite + Tailwind | Current checked-in SPA stack |
| Backend API | FastAPI + Uvicorn | Current checked-in backend stack |
| Language | Python 3.11+ and JavaScript | Matches backend and frontend code |
| Database | SQLite for local dev; PostgreSQL for production | SQLAlchemy supports both; production should use managed PostgreSQL |
| Cache / Queue | Optional Azure Cache for Redis | Not required by current code; useful for future schema/session cache and async jobs |
| Job Queue | Future: Azure Container Apps jobs, Azure Functions, or Redis-backed workers | Current code runs synchronously inside FastAPI |
| Secret Storage | Azure Key Vault | Production storage for app secrets and credential roots |
| AI | OpenAI API or Azure OpenAI Service | Current code has OpenAI client and Azure OpenAI configuration |
| Auth | Local auth + OTP, Google/GitHub OAuth, future Microsoft Entra ID | Matches current code and Azure enterprise path |
| Search | Postgres full-text (→ Typesense in Phase 3) | Marketplace discovery |
| Infra | Azure Static Web Apps, Azure Container Apps, Azure Database for PostgreSQL, Blob Storage, Key Vault | Managed Azure PaaS deployment |
| CI/CD | GitHub Actions or Azure DevOps | Standard Azure deployment paths |
| Observability | OpenTelemetry → Application Insights + Log Analytics | Traces, metrics, logs |

---

## 8. Phase-by-Phase Architecture Rollout

### Phase 1 (Weeks 0–6): Foundation

```
Components built:
- Portal (React/Vite) with API creation flows
- Core API service (FastAPI modular monolith)
- API Registry (SQLAlchemy models, SQLite locally, PostgreSQL in production)
- Basic MCP/ChatGPT bridge and tool registry
- Auth (local auth, OTP, OAuth hooks, JWT)

Azure infra: Static Web Apps + Container Apps + PostgreSQL Flexible Server + Key Vault
```

### Phase 2 (Weeks 6–12): Intelligence

```
New components:
- AI Assist service (schema suggestions, descriptions)
- Execution Engine (proxy with auth injection)
- Test Console (real API calls from browser)
- Schema Translator (OpenAI tools now, other adapters later)
- Execution logs

Azure infra: Keep execution in Container Apps initially.
       Add Azure Cache for Redis or a worker pattern only when async load requires it.
```

### Phase 3 (Weeks 12–18): Marketplace

```
New components:
- Marketplace search (Typesense)
- Auto API triggering (Execution Engine → MCP streaming)
- Analytics service
- Auth Vault (Azure Key Vault integration)
- OAuth2 flow for user-facing OAuth APIs

Azure infra: Add Front Door WAF, private endpoints, controlled egress, and read replica for analytics if needed
```

### Phase 4 (Weeks 18+): Scale & Monetization

```
New components:
- Workflow orchestration (multi-step API chaining)
- Billing service (usage metering)
- Enterprise features (SSO, audit logs, compliance)
- Full OAuth2 for API auth
- SDK: npm package for programmatic API registration
```

---

## 9. Key Architectural Decisions & Trade-offs

| Decision | Choice | Alternative | Reason |
|---|---|---|---|
| Modular monolith first | Yes | Microservices from day 1 | Faster iteration in Phase 1–2; extract when boundaries stabilize |
| JSONB for schemas | Postgres JSONB | Document DB (Mongo) | Avoid polyglot DB; JSONB is flexible enough and queryable |
| Proxy-based execution | Server-side proxy | Client-side fetch | Credential security: secrets never reach the browser |
| MCP over HTTP+SSE | Yes | WebSocket | MCP spec uses SSE; simpler firewall/proxy compatibility |
| Azure PaaS first | Yes | AKS from day 1 | Container Apps, Static Web Apps, managed PostgreSQL, and Key Vault match current scale with less platform overhead |
| LLM provider | OpenAI-compatible client with Azure OpenAI support | Single hard-coded provider | Lets local/mock, OpenAI, and Azure OpenAI deployments share the same app shape |
| Tenant isolation via RLS | Postgres RLS | App-level filtering | Defense in depth; SQL injection can't bypass RLS |

---

## 10. Scalability Considerations

- **Registry reads** are read-heavy → cache through Azure Cache for Redis when read load grows
- **Execution Engine** is stateless → horizontal scaling through Azure Container Apps replicas
- **AI Assist** calls are bursty → move long-running or high-volume parsing to Azure Container Apps jobs, Azure Functions, or a queue-backed worker when needed
- **MCP sessions** are lightweight metadata → keep in PostgreSQL initially; move hot/session TTL data to Redis if latency requires it
- **Execution logs** are write-heavy → keep operational summaries in PostgreSQL and export long-term logs to Log Analytics or Blob lifecycle storage

---

## 11. Observability

```
Every request emits:
├── Trace (OpenTelemetry) — request path across services
├── Metric — latency, error rate, throughput per API
└── Log — structured JSON, correlation ID

Key dashboards:
├── API execution success/error rate by workspace
├── AI Assist latency + cache hit rate
├── MCP session activity
└── Credential access audit log
```

---
