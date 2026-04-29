# Ways to Connect MCP Hub Tools to ChatGPT

Two integration paths are available. **Option A (Custom GPT Actions)** works today with any ChatGPT Plus account. **Option B (MCP Server)** is the emerging standard with native ChatGPT support.

---

## Option A — Custom GPT Actions

### How it works

ChatGPT Custom GPTs support "Actions" — you provide an OpenAPI 3.0 spec URL and ChatGPT discovers your tools automatically. When a user asks a question, ChatGPT decides which action to call, sends the HTTP request to your server, and incorporates the response into its reply.

```
User → Custom GPT → reads OpenAPI spec → calls your endpoint → returns result → GPT replies
```

### What needs to be built in MCP Hub

#### 1. Dynamic OpenAPI spec endpoint

Add `GET /api/chatgpt/openapi-spec` to your backend. It reads all **connected** APIs from the registry, converts each endpoint into an OpenAPI path, and returns a valid OpenAPI 3.0 JSON document.

```python
# backend/routers/chatgpt.py (new route)
@router.get("/openapi-spec")
def get_openapi_spec(db: Session = Depends(get_db)):
    connected = db.query(ApiDefinition).filter(ApiDefinition.is_connected == True).all()
    paths = {}
    for api in connected:
        for ep in api.endpoints:
            path_key = f"/{api.name.lower().replace(' ', '_')}/{ep.name}"
            paths[path_key] = {
                "post": {
                    "operationId": ep.name,
                    "summary": ep.description,
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": ep.input_schema or {"type": "object"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "Success"}}
                }
            }
    return {
        "openapi": "3.0.0",
        "info": {"title": "MCP Hub Tools", "version": "1.0.0"},
        "servers": [{"url": "https://your-domain.com"}],
        "paths": paths
    }
```

#### 2. Tool execution endpoint

Add `POST /api/chatgpt/actions/{tool_name}` — ChatGPT will call this with the arguments it decides to pass. Reuse the existing `_execute_tool` logic.

```python
@router.post("/actions/{tool_name}")
async def execute_action(tool_name: str, body: dict, db: Session = Depends(get_db)):
    # Find the endpoint by name across connected APIs
    ep = find_endpoint_by_name(tool_name, db)
    if not ep:
        raise HTTPException(404, f"Tool '{tool_name}' not found or not connected")
    result = await _execute_tool(ep, body)
    return {"result": result}
```

#### 3. Protect with API key auth

ChatGPT Actions support Bearer token authentication. Add an API key check so only your Custom GPT can call the endpoints:

```python
# In your FastAPI dependency
def verify_action_key(authorization: str = Header(...)):
    expected = f"Bearer {settings.chatgpt_action_key}"
    if authorization != expected:
        raise HTTPException(401, "Unauthorized")
```

Set `CHATGPT_ACTION_KEY=<random-secret>` in your `.env`.

### Setting up the Custom GPT

1. Go to [chat.openai.com](https://chat.openai.com) → **Explore GPTs** → **Create**
2. In the **Configure** tab, click **Create new action**
3. Set **Authentication** → Type: `API Key`, Auth type: `Bearer`, paste your `CHATGPT_ACTION_KEY`
4. In the schema field, paste your spec URL: `https://your-domain.com/api/chatgpt/openapi-spec`
5. Click **Import from URL** — ChatGPT will discover all your tools automatically
6. Save and publish the GPT

### Pros and Cons

| Pros | Cons |
|------|------|
| Works today, no waiting for rollouts | Requires a publicly accessible server (ngrok for local dev) |
| Full control over request/response format | Need to re-import spec when tools change |
| Supports all auth types via your existing `_build_auth` | Custom GPT only — not the main ChatGPT interface |
| Well-documented, stable API | |

### Local development with ngrok

```bash
# Expose your local backend publicly
ngrok http 8000

# Use the generated URL in your Custom GPT action
# e.g., https://abc123.ngrok.io/api/chatgpt/openapi-spec
```

---

## Option B — MCP Server (Model Context Protocol)

### How it works

MCP (Model Context Protocol) is an open standard by Anthropic that lets AI assistants discover and call tools via a standardised server protocol. OpenAI added MCP support to ChatGPT in early 2025. Users add your server as a **remote MCP server** in ChatGPT settings, and all tools become available natively — no Custom GPT required.

```
User → ChatGPT (MCP client) → connects to your MCP server → lists tools → calls tools → replies
```

### MCP transport options

| Transport | Description | Best for |
|-----------|-------------|----------|
| **HTTP + SSE** | Server-Sent Events for streaming | Remote hosted servers |
| **Streamable HTTP** | Newer, single endpoint | Simpler deployments |
| **stdio** | Local process stdin/stdout | Local dev tools |

For ChatGPT integration, **Streamable HTTP** is recommended.

### What needs to be built in MCP Hub

#### 1. Install the MCP Python SDK

```bash
pip install mcp
```

#### 2. Create an MCP server layer

Add `backend/mcp_server.py`:

```python
from mcp.server.fastmcp import FastMCP
from database import get_db
from models.api_definition import ApiDefinition
from routers.chatgpt import _execute_tool

mcp = FastMCP("MCP Hub")

def register_tools_from_db():
    db = next(get_db())
    connected = db.query(ApiDefinition).filter(ApiDefinition.is_connected == True).all()
    for api in connected:
        for ep in api.endpoints:
            # Dynamically register each endpoint as an MCP tool
            _register_tool(mcp, api, ep)

def _register_tool(mcp_instance, api, ep):
    tool_name = ep.name

    @mcp_instance.tool(name=tool_name, description=ep.description or "")
    async def tool_handler(**kwargs):
        return await _execute_tool(ep, kwargs)

register_tools_from_db()
```

#### 3. Mount the MCP server into FastAPI

In `backend/main.py`:

```python
from mcp_server import mcp

# Mount MCP server at /mcp
app.mount("/mcp", mcp.streamable_http_app())
```

Your MCP server will then be available at:
```
https://your-domain.com/mcp
```

#### 4. Re-register tools on connect/disconnect

When a user connects or disconnects an API in the UI, the MCP server's tool list must update. Add a refresh call in the connect/disconnect routes:

```python
# In routers/chatgpt.py after toggling is_connected
from mcp_server import register_tools_from_db
register_tools_from_db()
```

### Adding to ChatGPT

> Requires ChatGPT Plus, Teams, or Enterprise.

1. Go to **ChatGPT Settings** → **Connectors** → **Add MCP server**
2. Enter your server URL: `https://your-domain.com/mcp`
3. If auth is required, provide your API key
4. ChatGPT will list available tools — enable the ones you want
5. Tools are now available in any conversation

### Authentication for MCP

The MCP spec supports OAuth 2.0 for remote servers. For a simpler setup, use HTTP Bearer in a middleware:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def mcp_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        token = request.headers.get("Authorization", "")
        if token != f"Bearer {settings.mcp_secret_key}":
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)
```

### Pros and Cons

| Pros | Cons |
|------|------|
| Native in ChatGPT — no Custom GPT needed | Requires ChatGPT Plus/Teams/Enterprise |
| Works across all conversations automatically | MCP support in ChatGPT is still rolling out (2025) |
| Same server works for Claude, Cursor, and other MCP clients | Slightly more complex setup |
| Open standard — future-proof | Dynamic tool registration needs careful handling |

---

## Comparison Summary

| | Option A — Custom GPT Actions | Option B — MCP Server |
|---|---|---|
| **Works today** | Yes | Yes (ChatGPT Plus+) |
| **Setup complexity** | Medium | Medium–High |
| **Requires public server** | Yes | Yes |
| **Auth** | Bearer / API Key | Bearer / OAuth 2.0 |
| **Tool discovery** | Static OpenAPI spec import | Dynamic, live listing |
| **Scope** | Only your Custom GPT | Any MCP-compatible client |
| **Best for** | Quick integration, specific GPT | Multi-client, long-term solution |

---

## Recommended Path

**Start with Option A** — it's stable, well-documented, and can be running in under an hour. The main things to add to MCP Hub are the `/openapi-spec` endpoint and `/actions/{tool_name}` dispatcher, both of which reuse existing code.

**Add Option B later** as MCP support matures in ChatGPT and you want a single tool server that works across ChatGPT, Claude, Cursor, and other AI clients simultaneously.
