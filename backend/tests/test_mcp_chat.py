"""
Integration corner cases for POST /api/chatgpt/chat:
- No tools connected
- Fresh vs existing session
- Session cleared on disconnect
- Multi-turn parameter follow-up
- Mock LLM responses
"""
import os
os.environ["DATABASE_URL"]   = "sqlite:///:memory:"
os.environ["JWT_SECRET"]     = "test-secret"
os.environ["MOCK_LLM"]       = "true"
os.environ["OPENAI_API_KEY"] = "mock"
os.environ["ENCRYPTION_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from database import Base, engine
from main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _fresh_db():
    from models import agent_session, api_definition, auth_config, chatgpt_connection, user  # noqa
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/api/auth/register", json={
        "email": "test@test.com", "password": "pass123", "full_name": "Test"
    })
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def connected_api(client, auth):
    """Creates an API definition and connects it. Returns api_id."""
    # Create via manual builder
    payload = {
        "name": "Weather API",
        "base_url": "https://api.weather.com",
        "description": "Get weather data",
        "auth_type": "NONE",
        "endpoints": [{
            "name": "Get Weather",
            "path": "/weather",
            "method": "GET",
            "description": "Get current weather for a city",
            "parameters": [{"name": "city", "type": "string", "required": True,
                             "description": "City name"}],
        }],
    }
    r = client.post("/api/agent/manual", json=payload, headers=auth)
    assert r.status_code in (200, 201), r.text
    body = r.json()

    # Manual mode auto-saves; confirm only if still pending
    if body.get("state") not in ("SAVED",):
        session_id = body["id"]
        client.post(f"/api/agent/{session_id}/confirm", headers=auth)

    # Get API id from registry
    apis = client.get("/api/registry/", headers=auth).json()
    assert len(apis) > 0, "No APIs in registry after manual creation"
    api_id = apis[0]["id"]

    # Connect
    r = client.post(f"/api/chatgpt/connect/{api_id}", headers=auth)
    assert r.status_code == 200

    return api_id


# ── No tools connected ────────────────────────────────────────────────────────

def test_chat_no_tools_connected(client, auth):
    r = client.post("/api/chatgpt/chat",
                    json={"message": "what's the weather?"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "NO_TOOLS_CONNECTED"


# ── Mock LLM response ─────────────────────────────────────────────────────────

def test_chat_mock_mode_returns_mock_response(client, auth, connected_api):
    r = client.post("/api/chatgpt/chat",
                    json={"message": "what's the weather in London?"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "mock"
    assert "Mock mode" in body["response"]
    assert body["status"] == "ok"


# ── Session ID returned ───────────────────────────────────────────────────────

def test_chat_returns_session_id(client, auth, connected_api):
    r = client.post("/api/chatgpt/chat",
                    json={"message": "hello"}, headers=auth)
    body = r.json()
    assert "session_id" in body
    assert body["session_id"] != ""


def test_chat_same_session_id_on_follow_up(client, auth, connected_api):
    r1 = client.post("/api/chatgpt/chat",
                     json={"message": "hello", "session_id": None}, headers=auth)
    sid = r1.json()["session_id"]

    r2 = client.post("/api/chatgpt/chat",
                     json={"message": "follow up", "session_id": sid}, headers=auth)
    assert r2.json()["session_id"] == sid


# ── Session info endpoint ─────────────────────────────────────────────────────

def test_session_info_endpoint(client, auth, connected_api):
    r1  = client.post("/api/chatgpt/chat",
                      json={"message": "hi"}, headers=auth)
    sid = r1.json()["session_id"]

    r2 = client.get(f"/api/chatgpt/session/{sid}", headers=auth)
    assert r2.status_code == 200
    info = r2.json()
    assert info["session_id"] == sid
    assert "turns" in info


def test_session_info_404_for_unknown(client, auth):
    r = client.get("/api/chatgpt/session/bogus-id", headers=auth)
    assert r.status_code == 404


def test_session_clear_endpoint(client, auth, connected_api):
    r1  = client.post("/api/chatgpt/chat",
                      json={"message": "hi"}, headers=auth)
    sid = r1.json()["session_id"]

    r2 = client.delete(f"/api/chatgpt/session/{sid}", headers=auth)
    assert r2.status_code == 200
    assert r2.json()["cleared"] is True

    r3 = client.get(f"/api/chatgpt/session/{sid}", headers=auth)
    assert r3.status_code == 404


# ── Disconnect clears stats ───────────────────────────────────────────────────

def test_disconnect_reduces_connected_count(client, auth, connected_api):
    stats_before = client.get("/api/chatgpt/stats", headers=auth).json()
    assert stats_before["connected_apis"] == 1

    client.delete(f"/api/chatgpt/disconnect/{connected_api}", headers=auth)

    stats_after = client.get("/api/chatgpt/stats", headers=auth).json()
    assert stats_after["connected_apis"] == 0


def test_disconnect_nonexistent_returns_404(client, auth):
    r = client.delete("/api/chatgpt/disconnect/bad-id", headers=auth)
    assert r.status_code == 404


def test_connect_already_connected_is_idempotent(client, auth, connected_api):
    r = client.post(f"/api/chatgpt/connect/{connected_api}", headers=auth)
    assert r.status_code == 200
    assert "Already connected" in r.json()["message"]


# ── Registry with status ──────────────────────────────────────────────────────

def test_registry_shows_connection_status(client, auth, connected_api):
    items = client.get("/api/chatgpt/registry", headers=auth).json()
    assert len(items) == 1
    assert items[0]["is_connected"] is True
    assert items[0]["endpoint_count"] >= 1


def test_registry_empty_when_no_apis(client, auth):
    items = client.get("/api/chatgpt/registry", headers=auth).json()
    assert items == []


# ── Tool schema export ────────────────────────────────────────────────────────

def test_tools_schema_endpoint(client, auth, connected_api):
    r = client.get(f"/api/chatgpt/tools/{connected_api}", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["api_id"] == connected_api
    assert len(body["tools"]) >= 1
    tool = body["tools"][0]
    assert tool["type"] == "function"
    assert "function" in tool


def test_tools_schema_404_for_unknown(client, auth):
    r = client.get("/api/chatgpt/tools/bad-id", headers=auth)
    assert r.status_code == 404


# ── Auth guard ────────────────────────────────────────────────────────────────

def test_chat_requires_auth(client):
    r = client.post("/api/chatgpt/chat", json={"message": "hi"})
    assert r.status_code == 401


def test_stats_requires_auth(client):
    r = client.get("/api/chatgpt/stats")
    assert r.status_code == 401
