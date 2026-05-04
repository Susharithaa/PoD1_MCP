import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.api_definition import ApiDefinition
from models.operational import ExpenseReport, TransportationCost
from models.user import User
from translators.openai_translator import api_to_tools
from utils.auth import get_current_user, require_scope
from utils.masking import mask_sensitive
from utils.ssrf import validate_outbound_url
import httpx

router = APIRouter(prefix="/mcp", tags=["mcp"])


class JsonRpcEnvelope(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = {}


FIXED_MCP_TOOLS = [
    {
        "name": "hub.list_registered_apis",
        "description": "List API definitions available to the current user.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "hub.list_tools",
        "description": "List generated tool schemas for connected API definitions.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "hub.get_tool_schema",
        "description": "Fetch the generated tool schema for one API definition.",
        "inputSchema": {
            "type": "object",
            "properties": {"api_id": {"type": "string"}},
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
        "description": "Download a safe remote file URL and return metadata plus a masked text preview.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
    },
]


def _ok(envelope_id: str | int | None, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": envelope_id, "result": mask_sensitive(result)}


def _err(envelope_id: str | int | None, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": envelope_id, "error": {"code": code, "message": message}}


def _owned_apis(db: Session, user: User) -> list[ApiDefinition]:
    return db.query(ApiDefinition).filter(ApiDefinition.user_id == user.id).order_by(ApiDefinition.created_at.desc()).all()


def _handle_rpc(envelope: JsonRpcEnvelope, db: Session, user: User) -> dict:
    if envelope.jsonrpc != "2.0":
        return _err(envelope.id, -32600, "Invalid JSON-RPC version")
    if envelope.method == "initialize":
        return _ok(envelope.id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "MCP Hub", "version": "1.0.0"},
            "capabilities": {"tools": {}, "streaming": True},
        })
    if envelope.method == "tools/list":
        apis = _owned_apis(db, user)
        return _ok(envelope.id, {
            "tools": FIXED_MCP_TOOLS,
            "generatedTools": [tool for api in apis for tool in api_to_tools(api)],
        })
    if envelope.method == "resources/list":
        return _ok(envelope.id, {
            "resources": [
                {"uri": f"mcp-hub://api/{api.id}", "name": api.name, "mimeType": "application/json"}
                for api in _owned_apis(db, user)
            ]
        })
    if envelope.method == "tools/call":
        tool_name = envelope.params.get("name")
        args = envelope.params.get("arguments") or {}
        if tool_name == "hub.list_registered_apis":
            return _ok(envelope.id, [{"id": api.id, "name": api.name, "base_url": api.base_url} for api in _owned_apis(db, user)])
        if tool_name == "hub.list_tools":
            return _ok(envelope.id, [tool for api in _owned_apis(db, user) for tool in api_to_tools(api)])
        if tool_name == "hub.get_tool_schema":
            api = db.query(ApiDefinition).filter(ApiDefinition.id == args.get("api_id"), ApiDefinition.user_id == user.id).first()
            if not api:
                return _err(envelope.id, -32004, "API not found")
            return _ok(envelope.id, {"api_id": api.id, "api_name": api.name, "tools": api_to_tools(api)})
        if tool_name == "expense.get_application_info":
            return _ok(envelope.id, {
                "name": "MCP Hub Expense Reimbursement",
                "domain": "expense_report_transportation_cost",
                "capabilities": ["list_reports", "download_file", "transportation_costs"],
            })
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
                        {
                            "transport_type": c.transport_type,
                            "origin": c.origin,
                            "destination": c.destination,
                            "amount": c.amount,
                            "currency": c.currency,
                        }
                        for c in costs
                    ],
                })
            return _ok(envelope.id, result)
        if tool_name == "expense.download_file":
            url = args.get("url")
            if not url:
                return _err(envelope.id, -32602, "url is required")
            try:
                validate_outbound_url(url)
                with httpx.Client(timeout=5.0, follow_redirects=True, verify=False) as client:
                    response = client.get(url)
                response.raise_for_status()
            except Exception as exc:
                return _err(envelope.id, -32010, f"Download failed: {exc}")
            return _ok(envelope.id, {
                "url": url,
                "content_type": response.headers.get("content-type"),
                "size": len(response.content),
                "preview": response.text[:1000] if "text" in response.headers.get("content-type", "") else "",
            })
        return _err(envelope.id, -32601, f"Unknown tool: {tool_name}")
    return _err(envelope.id, -32601, f"Unknown method: {envelope.method}")


@router.post("")
def json_rpc(
    envelope: JsonRpcEnvelope,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("mcp:read")),
):
    return _handle_rpc(envelope, db, current_user)


@router.post("/stream")
def streamable_http(
    envelope: JsonRpcEnvelope,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("mcp:read")),
):
    request_id = str(uuid.uuid4())

    async def events():
        yield json.dumps({"event": "start", "request_id": request_id}) + "\n"
        yield json.dumps(_handle_rpc(envelope, db, current_user)) + "\n"
        yield json.dumps({"event": "end", "request_id": request_id}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@router.get("/sse")
def sse_transport(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("mcp:read")),
):
    async def events():
        init = JsonRpcEnvelope(id="sse-init", method="initialize")
        payload = _handle_rpc(init, db, current_user)
        yield f"event: message\ndata: {json.dumps(payload)}\n\n"
        tools = JsonRpcEnvelope(id="sse-tools", method="tools/list")
        yield f"event: message\ndata: {json.dumps(_handle_rpc(tools, db, current_user))}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
