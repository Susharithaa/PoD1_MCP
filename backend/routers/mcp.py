"""
MCP (Model Context Protocol) server — HTTP + SSE transports.

Endpoints:
  POST /mcp          — JSON-RPC 2.0 (initialize / tools/list / tools/call)
  POST /mcp/stream   — Streamable HTTP (same protocol, NDJSON response)
  GET  /mcp/sse      — SSE transport (server pushes initialize + tools/list on connect)
  GET  /mcp/info     — Human-readable server info (no auth required)

Auth:
  All protected endpoints accept:
    • Authorization: Bearer <jwt>          (login JWT)
    • Authorization: Bearer mcp_<token>    (API token with mcp:read scope, created in Security)

Codex CLI usage:
    1. Create an API token in MCP Hub → Security with scope "mcp:read"
    2. mcp add --name "mcp-hub" --transport http http://localhost:8000/mcp \\
           --header "Authorization: Bearer <your_token>"
"""

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.api_definition import ApiDefinition
from models.operational import ExpenseReport, TransportationCost
from models.user import User
from orchestrator.tool_orchestrator import _http_call
from translators.openai_translator import (
    _friendly_tool_name,
    _sanitize_schema,
    resolve_tool_call,
)
from utils.auth import get_current_user, require_scope
from utils.masking import mask_sensitive
from utils.remote_fetch import fetch_remote_text

router = APIRouter(prefix="/mcp", tags=["mcp"])

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "MCP Hub", "version": "1.0.0"}

# ── Fixed built-in tools ──────────────────────────────────────────────────────

FIXED_MCP_TOOLS = [
    {
        "name": "hub.list_registered_apis",
        "description": "List all API definitions registered in MCP Hub for the current user.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "hub.list_tools",
        "description": "List all callable tool schemas (registered API endpoints) for the current user.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "hub.get_tool_schema",
        "description": "Fetch the full tool schema for a specific API definition by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"api_id": {"type": "string", "description": "API definition ID"}},
            "required": ["api_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "expense.get_application_info",
        "description": "Get expense reimbursement application metadata and capabilities.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "expense.list_reports",
        "description": "List normalized expense reports for the current user.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "expense.download_file",
        "description": "Download a safe remote file URL and return metadata plus a text preview.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(req_id: str | int | None, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": mask_sensitive(result)}


def _err(req_id: str | int | None, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _content(text: str) -> list[dict]:
    return [{"type": "text", "text": text}]


def _owned_apis(db: Session, user: User) -> list[ApiDefinition]:
    q = db.query(ApiDefinition)
    if user.role != "admin":
        q = q.filter(ApiDefinition.user_id == user.id)
    return q.order_by(ApiDefinition.created_at.desc()).all()


def _build_api_tools(apis: list[ApiDefinition]) -> list[dict]:
    """Convert registered API endpoints to MCP tool schema format."""
    tools = []
    for api in apis:
        for ep in api.endpoints or []:
            raw = ep.input_schema if isinstance(ep.input_schema, dict) else {}
            schema = _sanitize_schema(raw)
            if schema.get("type") != "object":
                schema = {"type": "object", "properties": {}}
            tools.append({
                "name": _friendly_tool_name(api, ep),
                "description": f"{api.name}: {ep.description or ep.name or f'{ep.method} {ep.path}'}",
                "inputSchema": schema,
            })
    return tools


# ── Core RPC dispatcher (async to support _http_call) ────────────────────────

async def _dispatch(method: str, params: dict, req_id: Any, db: Session, user: User) -> dict:
    apis = _owned_apis(db, user)

    # ── initialize ────────────────────────────────────────────────────────────
    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "serverInfo": SERVER_INFO,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {},
            },
            "instructions": (
                "MCP Hub exposes your registered API tools alongside built-in hub and expense tools. "
                "Call tools/list to see everything available to you."
            ),
        })

    # ── notifications/initialized (no response expected) ─────────────────────
    if method == "notifications/initialized":
        return {}   # caller should not send this back

    # ── tools/list ────────────────────────────────────────────────────────────
    if method == "tools/list":
        api_tools = _build_api_tools(apis)
        return _ok(req_id, {"tools": FIXED_MCP_TOOLS + api_tools})

    # ── resources/list ────────────────────────────────────────────────────────
    if method == "resources/list":
        return _ok(req_id, {
            "resources": [
                {
                    "uri":      f"mcp-hub://api/{api.id}",
                    "name":     api.name,
                    "mimeType": "application/json",
                }
                for api in apis
            ]
        })

    # ── tools/call ────────────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments") or {}

        # Built-in hub tools
        if tool_name == "hub.list_registered_apis":
            return _ok(req_id, _content(json.dumps([
                {"id": api.id, "name": api.name, "base_url": api.base_url}
                for api in apis
            ])))

        if tool_name == "hub.list_tools":
            return _ok(req_id, _content(json.dumps(_build_api_tools(apis))))

        if tool_name == "hub.get_tool_schema":
            api = next((a for a in apis if a.id == args.get("api_id")), None)
            if not api:
                return _ok(req_id, {"content": _content("API not found"), "isError": True})
            from translators.openai_translator import api_to_tools
            return _ok(req_id, _content(json.dumps({"api_id": api.id, "api_name": api.name, "tools": api_to_tools(api)})))

        # Built-in expense tools
        if tool_name == "expense.get_application_info":
            return _ok(req_id, _content(json.dumps({
                "name": "MCP Hub Expense Reimbursement",
                "domain": "expense_report_transportation_cost",
                "capabilities": ["list_reports", "download_file"],
            })))

        if tool_name == "expense.list_reports":
            rows = db.query(ExpenseReport).filter(ExpenseReport.user_id == user.id).order_by(ExpenseReport.created_at.desc()).all()
            result = []
            for report in rows:
                costs = db.query(TransportationCost).filter(TransportationCost.report_id == report.id).all()
                result.append({
                    "id": report.id,
                    "employee_name": report.employee_name,
                    "report_number": report.report_number,
                    "status": report.status,
                    "currency": report.currency,
                    "total_amount": report.total_amount,
                    "transportation_costs": [
                        {"transport_type": c.transport_type, "origin": c.origin,
                         "destination": c.destination, "amount": c.amount, "currency": c.currency}
                        for c in costs
                    ],
                })
            return _ok(req_id, _content(json.dumps(result)))

        if tool_name == "expense.download_file":
            url = args.get("url")
            if not url:
                return _err(req_id, -32602, "url is required")
            try:
                result = fetch_remote_text(url, timeout_s=5.0)
                return _ok(req_id, _content(json.dumps(result.as_dict())))
            except Exception as exc:
                return _ok(req_id, {"content": _content(f"Download failed: {exc}"), "isError": True})

        # ── Registered API endpoint tools (dynamic) ───────────────────────────
        api_obj, ep_obj = resolve_tool_call(tool_name, db)
        if api_obj and ep_obj:
            result_text, success = await _http_call(api_obj, ep_obj, args)
            return _ok(req_id, {
                "content": _content(result_text),
                "isError": not success,
            })

        return _err(req_id, -32601, f"Unknown tool: {tool_name!r}. Call tools/list to see available tools.")

    return _err(req_id, -32601, f"Unknown method: {method!r}")


# ── Request parsing ───────────────────────────────────────────────────────────

class JsonRpcEnvelope(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = {}


# ── HTTP endpoints ────────────────────────────────────────────────────────────

@router.get("/info")
def mcp_info():
    """Public endpoint — returns server info and connection instructions."""
    return {
        "server": SERVER_INFO,
        "protocol": MCP_PROTOCOL_VERSION,
        "transports": {
            "http":  "POST /mcp          (JSON-RPC 2.0, Authorization: Bearer <token>)",
            "stream":"POST /mcp/stream   (Streamable HTTP, NDJSON)",
            "sse":   "GET  /mcp/sse      (SSE, Authorization: Bearer <token>)",
        },
        "auth": (
            "Create an API token in MCP Hub → Security page with scope 'mcp:read', "
            "then pass it as: Authorization: Bearer <token>"
        ),
        "codex_cli": (
            "mcp add --name mcp-hub --transport http http://localhost:8000/mcp "
            "--header \"Authorization: Bearer <your_token>\""
        ),
    }


@router.post("")
async def json_rpc(
    envelope: JsonRpcEnvelope,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("mcp:read")),
):
    """Primary JSON-RPC 2.0 endpoint. Supports initialize / tools/list / tools/call."""
    if envelope.jsonrpc != "2.0":
        return _err(envelope.id, -32600, "Invalid JSON-RPC version — must be '2.0'")

    # Notifications have no id and expect no response body
    if envelope.id is None and envelope.method.startswith("notifications/"):
        await _dispatch(envelope.method, envelope.params, None, db, current_user)
        return JSONResponse(content=None, status_code=204)

    result = await _dispatch(envelope.method, envelope.params, envelope.id, db, current_user)
    return result


@router.post("/stream")
async def streamable_http(
    envelope: JsonRpcEnvelope,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("mcp:read")),
):
    """
    Streamable HTTP transport — returns NDJSON.
    Each line is a JSON object: start event, the RPC result, then end event.
    """
    request_id = str(uuid.uuid4())
    result = await _dispatch(envelope.method, envelope.params, envelope.id, db, current_user)

    async def _lines():
        yield json.dumps({"event": "start",  "request_id": request_id}) + "\n"
        yield json.dumps(result) + "\n"
        yield json.dumps({"event": "end",    "request_id": request_id}) + "\n"

    return StreamingResponse(_lines(), media_type="application/x-ndjson")


@router.get("/sse")
async def sse_transport(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("mcp:read")),
):
    """
    SSE transport — server pushes initialize result and full tools/list on connect.
    Clients that use SSE for reading should POST requests to POST /mcp.
    """
    init_result  = await _dispatch("initialize",  {}, "sse-init",  db, current_user)
    tools_result = await _dispatch("tools/list",  {}, "sse-tools", db, current_user)

    async def _events():
        yield f"event: message\ndata: {json.dumps(init_result)}\n\n"
        yield f"event: message\ndata: {json.dumps(tools_result)}\n\n"
        # Keep connection alive with periodic pings
        try:
            while True:
                if await request.is_disconnected():
                    break
                yield ": ping\n\n"
                await asyncio.sleep(15)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(_events(), media_type="text/event-stream")
