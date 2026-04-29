"""Tests: manual API builder (ChatBuilder flow) and HITL validation."""
import pytest


def _auth(client):
    r = client.post("/api/auth/register", json={"email": "dev@test.com", "password": "pass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


MINIMAL_API = {
    "name": "Weather API",
    "base_url": "https://api.weather.example.com",
    "version": "1.0.0",
    "description": "Fetch weather data",
    "auth_type": "none",
    "auth_header": "",
    "auth_credentials": None,
    "endpoints": [
        {
            "method": "GET",
            "path": "/forecast",
            "name": "Get Forecast",
            "description": "Returns weather forecast",
            "auth_type": "",
            "parameters": [
                {"name": "city", "type": "string", "required": True, "description": "City name"},
            ],
        }
    ],
}


def test_manual_create_returns_session(client):
    headers = _auth(client)
    r = client.post("/api/agent/manual", json=MINIMAL_API, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["mode"] == "MANUAL"
    assert data["state"] in ("HITL_PENDING", "SAVED", "VALIDATING")


def test_manual_with_bearer_auth(client):
    headers = _auth(client)
    api = {**MINIMAL_API, "auth_type": "bearer", "auth_credentials": {
        "type": "bearer", "token": "my-secret-token",
    }}
    r = client.post("/api/agent/manual", json=api, headers=headers)
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Verify token is NOT stored as plain text
    r2 = client.get(f"/api/agent/{session_id}", headers=headers)
    session = r2.json()
    # auth_credentials field should be None or encrypted (not contain plain token)
    creds = session.get("auth_credentials")
    if creds:
        assert "my-secret-token" not in str(creds)


def test_get_session_requires_auth(client):
    r = client.get("/api/agent/some-id")
    assert r.status_code == 401


def test_get_session_not_found(client):
    headers = _auth(client)
    r = client.get("/api/agent/nonexistent-id", headers=headers)
    assert r.status_code == 404


def test_cannot_access_other_users_session(client):
    # User A creates a session
    r1 = client.post("/api/auth/register", json={"email": "a@test.com", "password": "pass"})
    ha = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    sess = client.post("/api/agent/manual", json=MINIMAL_API, headers=ha).json()
    session_id = sess["id"]

    # User B tries to read it
    r2 = client.post("/api/auth/register", json={"email": "b@test.com", "password": "pass"})
    hb = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    r3 = client.get(f"/api/agent/{session_id}", headers=hb)
    assert r3.status_code == 404


def test_manual_missing_base_url_rejected(client):
    headers = _auth(client)
    api = {**MINIMAL_API}
    del api["base_url"]
    # base_url is required — Pydantic rejects missing required field
    r = client.post("/api/agent/manual", json=api, headers=headers)
    assert r.status_code == 422


def test_manual_missing_endpoint_path(client):
    headers = _auth(client)
    api = {**MINIMAL_API, "endpoints": [{"method": "GET", "path": "", "name": "x", "description": "", "auth_type": "", "parameters": []}]}
    r = client.post("/api/agent/manual", json=api, headers=headers)
    # Path validation happens inside the agent — session may be HITL_PENDING with error
    assert r.status_code in (201, 422)
