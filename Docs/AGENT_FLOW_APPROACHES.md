# MCP Hub — Agent Flow Approaches

> **Context:** This document evaluates three architectural patterns for the
> API-creation agent pipeline: DOC/Chat input → Parsing → Create API → Validate.
> Tech stack: FastAPI · React Router · SQLite · OpenAI GPT-4o

---

## Overview

The agent flow must handle two entry modes and one mandatory human gate:

```
Entry Mode A: User types natural-language intent (Chat)
Entry Mode B: User uploads a document / Swagger / PDF (Doc)

                     ┌──────────────────────────────┐
  Chat ─────────────►│                              │
                     │   Agent Pipeline             │──► API saved to registry
  Doc  ─────────────►│                              │
                     └──────────────────────────────┘
                               contains:
                       Classify → Parse → Schema
                       → Confidence Score → [HITL] → Validate → Save
```

---

## Option A — Linear Pipeline (Simple Agent Chain)

### How it works

Each step is a discrete function called in sequence. Output of one is the
input of the next. No shared state object — data is passed as return values.

```
Input (Doc or Chat text)
        │
        ▼
[InputClassifier]         classify mode, extract raw text
        │
        ▼
[ParsingAgent]            LLM call → endpoints, params, auth, base_url
        │
        ▼
[SchemaAgent]             LLM call → draft OpenAPI schema
        │
        ▼
[ConfidenceAgent]         LLM call → per-field confidence scores
        │
        ▼
[HITL Gate]               pause, return draft to frontend
        │
   (human edits)
        │
        ▼
[SchemaValidator]         rule-based validation of edited schema
        │
        ▼
[ApiSaver]                INSERT into SQLite
```

### Implementation sketch

```python
async def run_pipeline(input_text: str, mode: str) -> DraftAPI:
    raw        = InputClassifier.run(input_text, mode)
    extracted  = await ParsingAgent.run(raw)
    draft      = await SchemaAgent.run(extracted)
    confidence = await ConfidenceAgent.run(draft)
    return DraftAPI(draft=draft, confidence=confidence)

# After HITL:
async def confirm_pipeline(draft: DraftAPI, edits: dict) -> str:
    merged    = merge_edits(draft, edits)
    validated = SchemaValidator.run(merged)
    api_id    = await ApiSaver.run(validated)
    return api_id
```

### Trade-offs

| Aspect | Detail |
|---|---|
| Complexity | Very low — linear function calls |
| Debuggability | High — stack trace shows exact failure point |
| HITL support | Weak — requires external state storage (session dict in Redis/DB) |
| Error recovery | None — a failed step breaks the whole chain |
| Retry logic | Must be added manually around each call |
| Extensibility | Poor — adding a branch (e.g. re-parse after HITL) requires restructuring |
| Best for | Prototyping, Phase 1, teams new to agents |

### When to choose

- Phase 1 MVP where speed of delivery matters most
- Small team, low operational complexity needed
- HITL can be a simple "save state → reload on confirm" without resumable sessions

---

## Option B — Orchestrator + Worker Agents (Recommended for v1 production)

### How it works

A central `AgentOrchestrator` owns a persistent `AgentSession` object stored
in SQLite. It calls worker agents in sequence but manages state transitions,
errors, and retries itself. HITL is a natural pause: the orchestrator saves
`state = HITL_PENDING` and returns — the session resumes when the human confirms.

```
FastAPI Route
      │
      ▼
AgentOrchestrator(session_id)
      │
      ├── [InputClassifier]     session.state = CLASSIFYING
      │         │
      │         ▼
      ├── [ParsingAgent]        session.state = PARSING
      │         │
      │         ▼
      ├── [SchemaAgent]         session.state = SCHEMA_GENERATING
      │         │
      │         ▼
      ├── [ConfidenceAgent]     session.state = CONFIDENCE_SCORING
      │         │
      │         ▼
      └── persist ──────────── session.state = HITL_PENDING  ← returns here
                                        │
                              [... human edits via UI ...]
                                        │
                              POST /api/agent/{id}/confirm
                                        │
      ┌─────────────────────────────────┘
      │
      ├── [SchemaValidator]     session.state = VALIDATING
      │         │
      │    invalid? ──► session.state = HITL_PENDING (loop back)
      │         │
      │      valid
      │         ▼
      └── [ApiSaver]            session.state = SAVED
```

### AgentSession state machine

```
INIT
 │
 ▼
CLASSIFYING ──(error)──► FAILED
 │
 ▼
PARSING ──(error)──► FAILED
 │
 ▼
SCHEMA_GENERATING ──(error)──► FAILED
 │
 ▼
CONFIDENCE_SCORING ──(error)──► FAILED
 │
 ▼
HITL_PENDING  ◄────────────────────────────────────┐
 │                                                  │
 │ (human confirms)                                 │
 ▼                                                  │
VALIDATING ──(invalid)──────────────────────────────┘
 │
 │ (valid)
 ▼
SAVING ──(error)──► FAILED
 │
 ▼
SAVED
```

### AgentSession data model (SQLite)

```python
class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id                = Column(String, primary_key=True)   # UUID
    mode              = Column(String)                      # DOC | CHAT
    state             = Column(String, default="INIT")      # state machine
    raw_input         = Column(Text, nullable=True)         # chat text
    file_path         = Column(String, nullable=True)       # uploaded doc path
    extracted_schema  = Column(JSON, nullable=True)         # ParsingAgent output
    draft_api         = Column(JSON, nullable=True)         # SchemaAgent output
    confidence_map    = Column(JSON, nullable=True)         # ConfidenceAgent output
    human_edits       = Column(JSON, nullable=True)         # HITL edits
    validation_errors = Column(JSON, nullable=True)         # SchemaValidator errors
    final_api         = Column(JSON, nullable=True)         # post-HITL merged schema
    api_definition_id = Column(String, nullable=True)       # FK after save
    error_log         = Column(JSON, default=list)          # per-step errors
    created_at        = Column(DateTime)
    updated_at        = Column(DateTime)
```

### Trade-offs

| Aspect | Detail |
|---|---|
| Complexity | Moderate — one orchestrator class + 6 worker classes |
| Debuggability | High — state column shows exactly where failure occurred |
| HITL support | First-class — session persists in DB, user can close browser and return |
| Error recovery | Per-step try/except sets state=FAILED with error_log |
| Retry logic | Orchestrator can re-run a failed step without restarting |
| Extensibility | Good — add new worker agents without touching others |
| Async support | Full — each agent is async, orchestrator awaits each step |
| Best for | v1 production, teams wanting reliability + debuggability |

### When to choose

- **This is the recommended approach for the MCP Hub v1**
- HITL is a critical feature — persistent sessions make it robust
- FastAPI + SQLite can natively support this without external queue/broker
- Easy to migrate to Option C (LangGraph) later by replacing orchestrator internals

---

## Option C — LangGraph State Machine (Best for complex multi-agent v2)

### How it works

Uses LangGraph (built on LangChain) to define the agent pipeline as a
directed graph of nodes (agents) and edges (transitions). State is a typed
`TypedDict` that flows through the graph. HITL is implemented as an
`interrupt` — the graph pauses at a node, persists its checkpoint to DB,
and resumes when human input arrives.

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

builder = StateGraph(AgentState)

builder.add_node("classify",          classify_node)
builder.add_node("parse",             parse_node)
builder.add_node("generate_schema",   schema_node)
builder.add_node("score_confidence",  confidence_node)
builder.add_node("hitl",              hitl_node)       # interrupt here
builder.add_node("validate",          validate_node)
builder.add_node("save",              save_node)

builder.set_entry_point("classify")
builder.add_edge("classify",         "parse")
builder.add_edge("parse",            "generate_schema")
builder.add_edge("generate_schema",  "score_confidence")
builder.add_edge("score_confidence", "hitl")
builder.add_conditional_edges(
    "validate",
    lambda s: "save" if s["is_valid"] else "hitl"   # loop back on invalid
)
builder.add_edge("save", END)

memory = SqliteSaver.from_conn_string("mcp_hub.db")
graph  = builder.compile(checkpointer=memory, interrupt_before=["hitl"])
```

### Graph flow

```
[classify] ──► [parse] ──► [generate_schema] ──► [score_confidence]
                                                          │
                                                          ▼
                                                    [hitl] ◄──────────────┐
                                                       │                  │
                                                  (interrupt)             │
                                                       │                  │
                                               human reviews UI           │
                                                       │                  │
                                                  (resume)                │
                                                       │                  │
                                                       ▼                  │
                                                  [validate] ──(invalid)──┘
                                                       │
                                                   (valid)
                                                       │
                                                       ▼
                                                    [save] ──► END
```

### AgentState TypedDict

```python
class AgentState(TypedDict):
    mode:             str                  # DOC | CHAT
    raw_input:        str
    file_path:        Optional[str]
    extracted_schema: Optional[dict]
    draft_api:        Optional[dict]
    confidence_map:   Optional[dict]
    human_edits:      Optional[dict]
    is_valid:         bool
    validation_errors: List[str]
    final_api:        Optional[dict]
    api_definition_id: Optional[str]
```

### Trade-offs

| Aspect | Detail |
|---|---|
| Complexity | High — requires LangGraph, LangChain, checkpoint setup |
| Debuggability | Very high — LangSmith tracing, graph visualisation built-in |
| HITL support | Native — `interrupt_before` is a first-class LangGraph concept |
| Error recovery | Built-in retry policies per node |
| Streaming | Native — stream partial results token by token |
| Observability | LangSmith dashboard for full run traces |
| Dependencies | Adds `langgraph`, `langchain`, `langchain-anthropic` (~15 MB) |
| Best for | v2+, teams already using LangChain, complex branching flows |

### When to choose

- Phase 3+ when the pipeline grows (multi-step execution, workflow chaining)
- If LangSmith observability is valuable to the team
- When you need native streaming of agent progress to the frontend
- When branching complexity exceeds what a hand-rolled orchestrator handles cleanly

---

## Comparison Summary

| Criterion | Option A (Linear) | Option B (Orchestrator) | Option C (LangGraph) |
|---|:---:|:---:|:---:|
| Setup complexity | Low | Medium | High |
| HITL support | Manual | Native | Native |
| Persistent sessions | Manual | Native (SQLite) | Native (SQLite checkpoint) |
| Error recovery | None | Per-step | Built-in |
| Retry support | Manual | Manual | Built-in |
| Streaming | No | No | Yes |
| Observability | Logs only | State column | LangSmith |
| External dependencies | None | None | LangGraph + LangChain |
| Recommended phase | Phase 1 MVP | **Phase 1–3 (chosen)** | Phase 3+ |

---

## Decision: Option B

Option B is implemented in this codebase (`backend/agents/`). Rationale:

1. **HITL is critical** — persistent `AgentSession` in SQLite means users can
   close the browser during validation and return later; the session resumes
   from `HITL_PENDING` state exactly.

2. **No new dependencies** — runs on FastAPI + SQLAlchemy + Anthropic SDK
   already in the stack. No LangChain overhead in v1.

3. **Debuggability** — the `state` column tells operators exactly where a
   session failed. `error_log` stores the per-step exception.

4. **Upgradeable** — the `AgentOrchestrator` can be swapped for a LangGraph
   graph in Phase 3 without changing the FastAPI routes or frontend, since
   the session contract (session_id, state, draft_api, confidence_map) stays
   the same.

### Migration path to Option C

```
Phase 1–2: Option B  (hand-rolled orchestrator)
Phase 3:   Option C  (replace orchestrator internals with LangGraph graph)
           Keep:  same AgentSession SQLite table
           Keep:  same FastAPI routes
           Keep:  same React Router frontend
           Swap:  AgentOrchestrator.run() → graph.ainvoke()
```

---

## File structure (Option B implementation)

```
backend/
├── agents/
│   ├── orchestrator.py       AgentOrchestrator — owns session lifecycle
│   ├── base.py               BaseAgent abstract class
│   ├── input_classifier.py   Detect mode, extract raw text
│   ├── parsing_agent.py      LLM: extract endpoints / params / auth
│   ├── schema_agent.py       LLM: build OpenAPI-compatible draft
│   ├── confidence_agent.py   LLM: score each field
│   ├── schema_validator.py   Rule-based post-HITL validation
│   └── api_saver.py          Write to api_definitions table
├── models/
│   ├── agent_session.py      SQLAlchemy AgentSession model
│   ├── api_definition.py     SQLAlchemy ApiDefinition + ApiEndpoint models
│   └── auth_config.py        SQLAlchemy AuthConfig model
├── routers/
│   └── agent.py              POST /start, GET /{id}, POST /{id}/hitl, POST /{id}/confirm
├── schemas/
│   └── agent.py              Pydantic request/response schemas
├── llm/
│   └── client.py             Anthropic SDK wrapper with prompt caching
├── database.py               SQLAlchemy engine + session factory
└── main.py                   FastAPI app entry point
```
