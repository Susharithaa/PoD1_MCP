"""Tests: registry CRUD — update tool, auth, endpoint create/update/delete."""
import pytest

SIMPLE_API = {
    "name": "CRUD Test API",
    "base_url": "https://crud.example.com",
    "version": "1.0.0",
    "description": "For CRUD testing",
    "auth_type": "none",
    "auth_header": "",
    "auth_credentials": None,
    "endpoints": [
        {"method": "GET", "path": "/items", "name": "list_items", "description": "", "auth_type": "", "parameters": []},
        {"method": "POST", "path": "/items", "name": "create_item", "description": "", "auth_type": "",
         "parameters": [{"name": "body", "type": "string", "required": True, "description": ""}]},
    ],
}


def _auth(client, email="crud@test.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "pass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _setup(client):
    h = _auth(client)
    client.post("/api/agent/manual", json=SIMPLE_API, headers=h)
    items = client.get("/api/registry/", headers=h).json()
    assert len(items) >= 1
    api_id = items[0]["id"]
    return h, api_id


# ── GET detail includes endpoints ────────────────────────────────────────────

def test_get_detail_includes_endpoints(client):
    h, api_id = _setup(client)
    r = client.get(f"/api/registry/{api_id}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "endpoints" in data
    assert len(data["endpoints"]) == 2
    paths = {ep["path"] for ep in data["endpoints"]}
    assert "/items" in paths


# ── PATCH tool metadata ──────────────────────────────────────────────────────

def test_patch_api_metadata(client):
    h, api_id = _setup(client)
    r = client.patch(f"/api/registry/{api_id}", headers=h,
                     json={"name": "Renamed API", "base_url": "https://new.example.com", "version": "2.0.0"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"]     == "Renamed API"
    assert data["base_url"] == "https://new.example.com"
    assert data["version"]  == "2.0.0"
    # endpoints untouched
    assert len(data["endpoints"]) == 2


def test_patch_partial_metadata(client):
    h, api_id = _setup(client)
    r = client.patch(f"/api/registry/{api_id}", headers=h, json={"name": "Only Name Changed"})
    assert r.status_code == 200
    assert r.json()["name"]     == "Only Name Changed"
    assert r.json()["base_url"] == SIMPLE_API["base_url"]


def test_patch_api_not_owned(client):
    h1, api_id = _setup(client)
    h2 = _auth(client, "other@test.com")
    r = client.patch(f"/api/registry/{api_id}", headers=h2, json={"name": "Hijacked"})
    assert r.status_code == 404


# ── PATCH auth ───────────────────────────────────────────────────────────────

def test_patch_auth_applies_to_all_endpoints(client):
    h, api_id = _setup(client)
    r = client.patch(f"/api/registry/{api_id}/auth", headers=h, json={"auth_type": "BEARER"})
    assert r.status_code == 200
    data = r.json()
    assert all(ep["auth_type"] == "BEARER" for ep in data["endpoints"])


def test_patch_auth_not_owned(client):
    h1, api_id = _setup(client)
    h2 = _auth(client, "thief@test.com")
    r = client.patch(f"/api/registry/{api_id}/auth", headers=h2, json={"auth_type": "BEARER"})
    assert r.status_code == 404


# ── POST endpoint ─────────────────────────────────────────────────────────────

def test_create_endpoint(client):
    h, api_id = _setup(client)
    new_ep = {
        "name": "delete_item", "description": "Delete an item",
        "path": "/items/{id}", "method": "DELETE", "auth_type": "BEARER",
        "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
        "output_schema": None, "headers": [],
    }
    r = client.post(f"/api/registry/{api_id}/endpoints", headers=h, json=new_ep)
    assert r.status_code == 201
    ep = r.json()
    assert ep["path"]      == "/items/{id}"
    assert ep["method"]    == "DELETE"
    assert ep["auth_type"] == "BEARER"
    assert ep["id"] is not None

    # Verify appears in detail
    detail = client.get(f"/api/registry/{api_id}", headers=h).json()
    assert len(detail["endpoints"]) == 3


def test_create_endpoint_not_owned(client):
    h1, api_id = _setup(client)
    h2 = _auth(client, "intruder@test.com")
    r = client.post(f"/api/registry/{api_id}/endpoints", headers=h2,
                    json={"name": "x", "path": "/x", "method": "GET", "auth_type": "NONE"})
    assert r.status_code == 404


# ── PUT endpoint ──────────────────────────────────────────────────────────────

def test_update_endpoint(client):
    h, api_id = _setup(client)
    ep_id = client.get(f"/api/registry/{api_id}", headers=h).json()["endpoints"][0]["id"]

    updated = {
        "name": "list_all_items", "description": "Updated description",
        "path": "/items", "method": "GET", "auth_type": "API_KEY",
        "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
        "output_schema": None, "headers": [],
    }
    r = client.put(f"/api/registry/{api_id}/endpoints/{ep_id}", headers=h, json=updated)
    assert r.status_code == 200
    ep = r.json()
    assert ep["name"]      == "list_all_items"
    assert ep["auth_type"] == "API_KEY"


def test_update_endpoint_wrong_api(client):
    h1, api_id1 = _setup(client)
    h2 = _auth(client, "w2@test.com")
    client.post("/api/agent/manual", json={**SIMPLE_API, "name": "API2"}, headers=h2)
    api2_id = client.get("/api/registry/", headers=h2).json()[0]["id"]
    ep_id   = client.get(f"/api/registry/{api2_id}", headers=h2).json()["endpoints"][0]["id"]

    # Try to update user2's endpoint via user1's api_id → 404
    r = client.put(f"/api/registry/{api_id1}/endpoints/{ep_id}", headers=h1,
                   json={"name": "x", "path": "/x", "method": "GET", "auth_type": "NONE",
                         "input_schema": None, "output_schema": None, "headers": []})
    assert r.status_code == 404


# ── DELETE endpoint ───────────────────────────────────────────────────────────

def test_delete_endpoint(client):
    h, api_id = _setup(client)
    ep_id = client.get(f"/api/registry/{api_id}", headers=h).json()["endpoints"][0]["id"]

    r = client.delete(f"/api/registry/{api_id}/endpoints/{ep_id}", headers=h)
    assert r.status_code == 204

    remaining = client.get(f"/api/registry/{api_id}", headers=h).json()["endpoints"]
    assert len(remaining) == 1
    assert all(ep["id"] != ep_id for ep in remaining)


def test_delete_endpoint_not_owned(client):
    h1, api_id = _setup(client)
    ep_id = client.get(f"/api/registry/{api_id}", headers=h1).json()["endpoints"][0]["id"]
    h2 = _auth(client, "del_thief@test.com")
    r = client.delete(f"/api/registry/{api_id}/endpoints/{ep_id}", headers=h2)
    assert r.status_code == 404


def test_delete_nonexistent_endpoint(client):
    h, api_id = _setup(client)
    r = client.delete(f"/api/registry/{api_id}/endpoints/nonexistent-id", headers=h)
    assert r.status_code == 404
