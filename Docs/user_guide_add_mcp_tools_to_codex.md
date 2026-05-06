# User Guide: Add MCP Hub Tools to Codex

This guide explains how to add an API as a tool in MCP Hub and connect those tools to Codex through the MCP server.

## What You Need

- MCP Hub backend running at `http://localhost:8000`
- MCP Hub frontend running at `http://localhost:5173`
- A registered MCP Hub user account
- Codex CLI or another MCP-compatible client
- For live API calls, the API you register must be reachable from the backend machine

For no-key local testing, set the backend to mock LLM mode:

```env
OPENAI_API_KEY=mock
MOCK_LLM=true
```

## 1. Start MCP Hub

Backend:

```bash
python run.py
```

Frontend:

```bash
cd frontend
npm run dev
```

Open the frontend:

```text
http://localhost:5173
```

## 2. Create Or Sign In To Your Account

1. Open `http://localhost:5173/register` for first-time setup, or `http://localhost:5173/login` if you already have an account.
2. Complete the OTP flow.
3. Keep this account in mind: MCP tools are scoped to the current user. Other users cannot discover or execute your registered APIs.

## 3. Add An API As A Tool

MCP Hub supports two common ways to add tools.

### Option A: API Builder

Use this when you know the API base URL, endpoints, parameters, and auth.

1. Go to **Create -> API Builder**.
2. Fill in:
   - API name
   - Base URL, for example `https://api.example.com`
   - Description
   - Authentication type, if needed
3. Add one or more endpoints:
   - HTTP method: `GET`, `POST`, `PUT`, `PATCH`, or `DELETE`
   - Path, for example `/weather`
   - Tool/endpoint name, for example `get_weather`
   - Parameters and required flags
4. Submit the form.
5. Review the validation screen.
6. Save the API.

After saving, the endpoint becomes a discoverable MCP tool.

### Option B: Document Upload

Use this when you have an OpenAPI, Swagger, text, Markdown, JSON, or PDF description.

1. Go to **Create -> Doc Upload**.
2. Upload a supported file:
   - `.yaml`
   - `.yml`
   - `.json`
   - `.txt`
   - `.md`
   - `.pdf`
3. Wait for the agent pipeline to parse the document.
4. Review the generated schema in the human-in-the-loop validation screen.
5. Fix any endpoint names, paths, auth settings, parameters, or schemas.
6. Save the API.

The saved endpoints become MCP tools.

## 4. Confirm The API Is In Your Registry

1. Go to **API Registry**.
2. Find the API you added.
3. Expand the API card or open **Manage**.
4. Confirm the endpoints are present.

The tool names exposed over MCP are based on endpoint names. For example:

```text
Get Weather -> get_weather
Private Forecast -> private_forecast
```

MCP Hub sanitizes names so they are safe for tool clients.

## 5. Create An MCP API Token

Codex should connect with an API token, not your browser login token.

If your UI has **Security -> API Tokens**:

1. Open **Security -> API Tokens**.
2. Create a new token.
3. Include this scope:

```text
mcp:read
```

4. Copy the token when it is shown.

If the Security page is not visible in your build, create the token through the backend API:

1. Sign in to the frontend.
2. Open browser dev tools.
3. Read the login JWT from local storage:

```javascript
localStorage.getItem("mcp_token")
```

4. Use that login JWT to create an MCP API token:

```bash
curl -X POST http://localhost:8000/api/security/tokens \
  -H "Authorization: Bearer <your_login_jwt_from_localStorage>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Codex MCP","scopes":["mcp:read"]}'
```

5. Copy the `token` field from the response. Use this `mcp_...` token for Codex.

The token starts with:

```text
mcp_
```

Store it securely. MCP Hub stores only the token hash, so you cannot view the full token again later.

## 6. Verify MCP Discovery Manually

Run:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer <your_mcp_token>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

You should see a JSON-RPC response containing:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": []
  }
}
```

The `tools` array should include:

- Built-in hub tools such as `hub.list_registered_apis`
- Built-in expense tools, if enabled
- Your registered API endpoint tools

You can also check server metadata in a browser:

```text
http://localhost:8000/mcp/info
```

## 7. Add MCP Hub To Codex

Use the MCP server URL:

```text
http://localhost:8000/mcp
```

Add it to Codex:

```bash
export MCP_HUB_TOKEN="<your_mcp_token>"

codex mcp add mcp-hub --url http://localhost:8000/mcp \
  --bearer-token-env-var MCP_HUB_TOKEN
```

After adding it, Codex should be able to discover tools from MCP Hub.

Check the server registration:

```bash
codex mcp get mcp-hub
```

It should show an HTTP/streamable URL configuration, not a stdio command with `http://localhost:8000/mcp` as the command.

Verify MCP discovery directly:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer $MCP_HUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

This should return the built-in hub tools and the API tools saved under the authenticated user. `codex mcp list` lists configured MCP servers; it does not list individual tools.

## 8. Test From Codex

Ask Codex to list available MCP tools or use one of your registered tools.

Useful test prompts:

```text
List the tools available from mcp-hub.
```

```text
Use the mcp-hub tool hub.list_registered_apis.
```

```text
Use my registered weather tool to get the forecast for Tokyo.
```

If the API endpoint requires parameters, Codex may ask you for missing values.

## 9. Available MCP Endpoints

The current backend exposes these MCP endpoints:

| Endpoint | Purpose | Auth |
|---|---|---|
| `POST /mcp` | Primary JSON-RPC endpoint for `initialize`, `tools/list`, `tools/call`, and `resources/list` | Bearer token with `mcp:read` |
| `POST /mcp/stream` | Streamable HTTP / NDJSON response | Bearer token with `mcp:read` |
| `GET /mcp/sse` | SSE transport that pushes initialize and tools/list events | Bearer token with `mcp:read` |
| `GET /mcp/info` | Human-readable server info | No auth |

For Codex, use:

```text
POST /mcp
```

## 10. Security And Scoping

MCP Hub scopes MCP discovery and execution to the authenticated user.

- A normal user only sees APIs they created.
- Admins can see all registered APIs.
- Dynamic MCP tool execution is scoped to the same API set as discovery.
- API credentials are decrypted only server-side when the backend executes the tool.
- Secrets and API tokens should never be pasted into docs, screenshots, commits, or chat.

## 11. Troubleshooting

### `401 Unauthorized`

The request is missing a Bearer token or the token is invalid.

Check:

```bash
-H "Authorization: Bearer <your_mcp_token>"
```

### `403 Missing scope: mcp:read`

The token exists but does not include the `mcp:read` scope.

Create a new token with:

```text
mcp:read
```

### `tools/list` returns only built-in tools

Your account does not have any saved API endpoints yet.

Check:

1. Go to **API Registry**.
2. Confirm the API is saved.
3. Confirm the endpoints are present.
4. Retry `tools/list`.

### Codex shows `Unsupported` or `transport: stdio`

The server was added with the URL as a command instead of an HTTP MCP URL.

Fix it by removing and re-adding the server:

```bash
codex mcp remove mcp-hub

export MCP_HUB_TOKEN="<your_mcp_token>"
codex mcp add mcp-hub --url http://localhost:8000/mcp \
  --bearer-token-env-var MCP_HUB_TOKEN

codex mcp get mcp-hub
```

The final command should show an HTTP/streamable URL configuration. Also make sure `MCP_HUB_TOKEN` is available in the shell where you run Codex.

### Tool exists but live call fails

Common causes:

- API base URL is wrong
- Endpoint path is wrong
- Required parameter is missing
- Auth credentials are missing or incorrect
- Backend cannot reach the target host
- SSRF protection blocked a private or unsafe destination
- `DRY_RUN_TOOLS=true` or `EMERGENCY_STOP=true`

### Local fake sample fails reachability

Some sample specs use:

```text
https://api.example.com
```

That host is only a placeholder. Use a real public API, or run the local sample FastAPI app and register its local base URL.

## 12. Quick End-To-End Checklist

1. Start backend on `http://localhost:8000`.
2. Start frontend on `http://localhost:5173`.
3. Register or log in.
4. Add an API through **API Builder** or **Doc Upload**.
5. Save the API after validation.
6. Confirm it appears in **API Registry**.
7. Create an API token with `mcp:read`.
8. Verify discovery with `curl` and `tools/list`.
9. Add MCP Hub to Codex with `codex mcp add --url`.
10. Ask Codex to list or call your MCP Hub tools.
