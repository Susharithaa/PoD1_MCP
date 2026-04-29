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
       │  Claude     │               │  APIs         │
       └─────────────┘               └───────────────┘
```

---

## 2. High-Level Architecture

### 2.1 Deployment Architecture

```
                        ┌──────────────┐
                        │   CDN/Edge   │  (Static assets, caching)
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  API Gateway │  (Rate limiting, routing, TLS termination)
                        └──────┬───────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
    │  Portal BFF  │  │  Core API    │  │  Execution       │
    │  (Next.js)   │  │  Service     │  │  Service         │
    └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
           │                 │                    │
           └─────────────────┼────────────────────┘
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
       ┌────────────┐ ┌────────────┐ ┌─────────────┐
       │ PostgreSQL │ │   Redis    │ │  Secrets    │
       │ (primary)  │ │ (cache +   │ │  Manager    │
       └────────────┘ │  queue)    │ └─────────────┘
                      └────────────┘
```

### 2.2 Service Decomposition (Modular Monolith → Microservices)

Start as a **modular monolith** in Phase 1–2, extract to microservices in Phase 3–4.

| Module | Responsibility | Phase Extracted |
|---|---|---|
| `registry` | CRUD for API definitions | Monolith |
| `schema` | Schema validation, translation, AI suggestions | Monolith → Phase 2 |
| `execution` | Proxy requests to real APIs | Phase 2 |
| `auth-vault` | Store and inject credentials | Phase 3 |
| `ai-assist` | LLM-powered schema/description generation | Phase 2 |
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
  OpenAI Tools      Anthropic Tools
  Format            Format (MCP)
```

- Supports pluggable adapters: `OpenAIAdapter`, `AnthropicAdapter`, `GenericMCPAdapter`
- Caches translated schemas in Redis (invalidated on API update)
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
- Hard timeout: 30s per execution
- Retry: 2 attempts with exponential backoff (network errors only)
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
│  Storage: Secrets Manager            │
│  (AWS Secrets Manager / Vault)       │
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

- Uses Claude (claude-sonnet-4-6) via Anthropic SDK with prompt caching
- Structured outputs enforced via tool use / response format constraints
- Rate-limited per workspace to control costs

---

### 3.6 MCP Bridge

Adapter that exposes the MCP Hub as an MCP server to LLM clients.

```
LLM Client (ChatGPT / Claude)
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
  secret_ref  -- pointer to Secrets Manager, never raw value
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
│  ├── Secrets stored in Secrets Manager only     │
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
| Frontend | Next.js 14 (App Router) | SSR, API routes as BFF |
| Backend API | Node.js + Fastify | Low overhead, schema validation built-in |
| Language | TypeScript | Type safety across stack |
| Database | PostgreSQL 16 | JSONB for schemas, RLS for tenant isolation |
| Cache / Queue | Redis (Upstash or self-hosted) | Sessions, schema cache, job queue |
| Job Queue | BullMQ (on Redis) | Async execution, retries |
| Secret Storage | AWS Secrets Manager (or HashiCorp Vault) | Credential security |
| AI | Anthropic SDK (claude-sonnet-4-6) | Schema suggestions, descriptions |
| Auth | Auth0 or Clerk | OAuth2 SSO, JWT management |
| Search | Postgres full-text (→ Typesense in Phase 3) | Marketplace discovery |
| Infra | AWS (ECS Fargate + RDS + ElastiCache) | Managed, scalable |
| CI/CD | GitHub Actions | Standard |
| Observability | OpenTelemetry → Grafana/Datadog | Traces, metrics, logs |

---

## 8. Phase-by-Phase Architecture Rollout

### Phase 1 (Weeks 0–6): Foundation

```
Components built:
- Portal (Next.js) with API creation wizard
- Core API service (monolith)
- API Registry (Postgres)
- Basic MCP Bridge (manual attach)
- Auth (JWT + workspace API keys)

Infra: Single ECS service + RDS + Redis
```

### Phase 2 (Weeks 6–12): Intelligence

```
New components:
- AI Assist service (schema suggestions, descriptions)
- Execution Engine (proxy with auth injection)
- Test Console (real API calls from browser)
- Schema Translator (OpenAI + Anthropic adapters)
- Execution logs

Infra: Extract Execution Engine to separate ECS service
       Add BullMQ for async execution
```

### Phase 3 (Weeks 12–18): Marketplace

```
New components:
- Marketplace search (Typesense)
- Auto API triggering (Execution Engine → MCP streaming)
- Analytics service
- Auth Vault (Secrets Manager integration)
- OAuth2 flow for user-facing OAuth APIs

Infra: Add CDN (CloudFront), add read replica for analytics
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
| Prompt caching (Anthropic) | Yes | No caching | Reduces AI Assist latency and cost for repeated schema patterns |
| Tenant isolation via RLS | Postgres RLS | App-level filtering | Defense in depth; SQL injection can't bypass RLS |

---

## 10. Scalability Considerations

- **Registry reads** are read-heavy → cached in Redis, CDN-cacheable for public APIs
- **Execution Engine** is stateless → horizontal scaling via ECS auto-scaling
- **AI Assist** calls are bursty → queue-backed with BullMQ, rate-limited per workspace
- **MCP sessions** are lightweight (metadata only) → stored in Redis with TTL
- **Execution logs** are write-heavy → partitioned Postgres table by month, archived to S3 after 30 days

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
