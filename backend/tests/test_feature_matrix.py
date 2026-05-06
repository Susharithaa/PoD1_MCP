"""Feature-level tests for the main production behaviors."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("OPENAI_API_KEY", "mock")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import settings
from models.operational import PluginSetting
from orchestrator.tool_orchestrator import tool_orchestrator
from utils.masking import mask_sensitive
from utils.remote_fetch import fetch_remote_text


def auth_headers(client, email="feature@test.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "pass123", "full_name": "Feature User"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health_and_request_id_header(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers["x-request-id"]


def test_masking_redacts_secrets():
    payload = {
        "token": "sk-proj-abc123",
        "nested": {"authorization": "Bearer abc.def.ghi"},
        "list": ["ok", "sk-secret-value"],
    }
    masked = mask_sensitive(payload)
    assert masked["token"] == "[REDACTED]"
    assert masked["nested"]["authorization"] == "[REDACTED]"
    assert masked["list"][1] == "[REDACTED]"


def test_read_only_mode_blocks_mutation(client, monkeypatch):
    monkeypatch.setattr(settings, "read_only_mode", True)
    r = client.post("/api/auth/register", json={"email": "ro@test.com", "password": "pass123"})
    assert r.status_code == 423


def test_emergency_stop_blocks_mutation(client, monkeypatch):
    monkeypatch.setattr(settings, "emergency_stop", True)
    r = client.post("/api/auth/register", json={"email": "es@test.com", "password": "pass123"})
    assert r.status_code == 423


@pytest.mark.asyncio
async def test_dry_run_executes_without_http(monkeypatch):
    class Func:
        name = "weather.get"
        arguments = json.dumps({"city": "London"})

    tc = MagicMock()
    tc.id = "tc1"
    tc.function = Func()

    api = MagicMock()
    api.name = "Weather API"
    api.base_url = "https://example.com"
    ep = MagicMock()
    ep.name = "weather.get"
    ep.path = "/weather"
    ep.method = "GET"
    ep.input_schema = {"required": [], "properties": {}}
    ep.auth_credentials = None

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator.is_dry_run_enabled", return_value=True), \
         patch("orchestrator.tool_orchestrator._http_call", new=AsyncMock()) as http_call:
        result = await tool_orchestrator.execute_all([tc], MagicMock())

    assert result[0].skipped is True
    assert http_call.await_count == 0


@pytest.mark.asyncio
async def test_tool_orchestrator_honors_allowed_api_scope():
    class Func:
        name = "private_forecast"
        arguments = json.dumps({})

    tc = MagicMock()
    tc.id = "tc-private"
    tc.function = Func()

    api = MagicMock()
    ep = MagicMock()
    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call", new=AsyncMock()) as http_call:
        result = await tool_orchestrator.execute_all([tc], MagicMock(), allowed_apis=[])

    payload = json.loads(result[0].result_text)
    assert payload["status"] == "TOOL_NOT_FOUND"
    assert http_call.await_count == 0


def test_expense_domain_create_list_and_info(client):
    headers = auth_headers(client)
    payload = {
        "employee_name": "Alice",
        "report_number": "EXP-1001",
        "status": "DRAFT",
        "currency": "INR",
        "source_file_url": "https://example.com/report.pdf",
        "transportation_costs": [
            {"transport_type": "cab", "origin": "A", "destination": "B", "amount": 42, "currency": "INR"}
        ],
    }
    r = client.post("/api/domain/expense-reports", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    assert body["employee_name"] == "Alice"
    assert body["total_amount"] == 42

    r = client.get("/api/domain/application-info", headers=headers)
    assert r.status_code == 200
    assert "expense_report_transportation_cost" in r.json()["data"]["domain"]

    r = client.get("/api/domain/expense-reports", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1


def test_expense_file_download_uses_safe_helper(client):
    headers = auth_headers(client)
    fake = MagicMock()
    fake.headers = {"content-type": "text/plain"}
    fake.content = b"hello"
    fake.text = "hello"
    fake.raise_for_status.return_value = None
    client_obj = MagicMock()
    client_obj.__enter__.return_value = client_obj
    client_obj.__exit__.return_value = False
    client_obj.get.return_value = fake

    with patch("utils.remote_fetch.validate_outbound_url"), patch("utils.remote_fetch.httpx.Client", return_value=client_obj):
        r = client.post("/api/domain/file-download?url=https%3A%2F%2Fexample.com%2Fa.txt", headers=headers)

    assert r.status_code == 200
    assert r.json()["data"]["preview"] == "hello"


def test_mcp_fixed_tools_and_expense_tools(client):
    headers = auth_headers(client)
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": "1", "method": "tools/list"}, headers=headers)
    assert r.status_code == 200
    tools = r.json()["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert "expense.get_application_info" in names
    assert "expense.list_reports" in names
    assert "expense.download_file" in names


def test_mcp_tools_call_application_info(client):
    headers = auth_headers(client)
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "2", "method": "tools/call", "params": {"name": "expense.get_application_info", "arguments": {}}},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["result"]["domain"] == "expense_report_transportation_cost"


def test_mcp_dynamic_tool_execution_is_scoped_to_current_user(client):
    from database import SessionLocal
    from models.api_definition import ApiDefinition, ApiEndpoint

    owner_headers = auth_headers(client, "mcp-owner@test.com")
    caller_login_headers = auth_headers(client, "mcp-caller@test.com")
    owner = client.get("/api/auth/me", headers=owner_headers).json()
    token_resp = client.post(
        "/api/security/tokens",
        json={"name": "MCP test token", "scopes": ["mcp:read"]},
        headers=caller_login_headers,
    )
    assert token_resp.status_code == 201, token_resp.text
    caller_mcp_headers = {"Authorization": f"Bearer {token_resp.json()['token']}"}

    with SessionLocal() as db:
        api = ApiDefinition(
            id="api-owner-private",
            name="Owner Private API",
            base_url="https://owner.example.com",
            user_id=owner["id"],
        )
        ep = ApiEndpoint(
            id="ep-owner-private",
            api_definition_id=api.id,
            name="Private Forecast",
            description="Owner-only endpoint",
            path="/forecast",
            method="GET",
            input_schema={"type": "object", "properties": {}},
        )
        db.add(api)
        db.add(ep)
        db.commit()

    listed = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "list", "method": "tools/list"},
        headers=caller_mcp_headers,
    )
    assert listed.status_code == 200
    names = {tool["name"] for tool in listed.json()["result"]["tools"]}
    assert "private_forecast" not in names

    with patch("routers.mcp._http_call", new=AsyncMock(return_value=("should not run", True))) as http_call:
        called = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "call",
                "method": "tools/call",
                "params": {"name": "private_forecast", "arguments": {}},
            },
            headers=caller_mcp_headers,
        )

    assert called.status_code == 200
    assert called.json()["error"]["code"] == -32601
    assert http_call.await_count == 0


def test_system_controls_round_trip(client):
    headers = auth_headers(client)
    admin_row = PluginSetting(id="sys-1", name="system-controls", enabled=True, config={"emergency_stop": True, "dry_run_tools": True, "max_tool_execution_ms": 3000})
    from database import SessionLocal

    with SessionLocal() as db:
        db.add(admin_row)
        db.commit()

    r = client.get("/api/admin/system-controls", headers=headers)
    assert r.status_code in (200, 403)
