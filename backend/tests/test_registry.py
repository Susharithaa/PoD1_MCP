"""Tests: API registry — list, get, delete, multi-tenancy isolation."""
import pytest


def _register_and_auth(client, email="user@test.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "pass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


SIMPLE_API = {
    "name": "Test API",
    "base_url": "https://api.example.com",
    "version": "1.0.0",
    "description": "A test API",
    "auth_type": "none",
    "auth_header": "",
    "auth_credentials": None,
    "endpoints": [{"method": "GET", "path": "/ping", "name": "Ping", "description": "", "auth_type": "", "parameters": []}],
}


def _create_api(client, headers):
    r = client.post("/api/agent/manual", json=SIMPLE_API, headers=headers)
    return r.json()


def test_registry_empty_for_new_user(client):
    h = _register_and_auth(client)
    r = client.get("/api/registry/", headers=h)
    assert r.status_code == 200
    assert r.json() == []


def test_registry_list_requires_auth(client):
    r = client.get("/api/registry/")
    assert r.status_code == 401


def test_registry_shows_saved_api(client):
    h = _register_and_auth(client)
    _create_api(client, h)
    r = client.get("/api/registry/", headers=h)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert items[0]["name"] == "Test API"


def test_registry_isolates_between_users(client):
    h1 = _register_and_auth(client, "user1@test.com")
    h2 = _register_and_auth(client, "user2@test.com")
    _create_api(client, h1)

    r = client.get("/api/registry/", headers=h2)
    assert r.json() == []


def test_registry_delete(client):
    h = _register_and_auth(client)
    _create_api(client, h)
    items = client.get("/api/registry/", headers=h).json()
    assert len(items) >= 1
    api_id = items[0]["id"]

    r = client.delete(f"/api/registry/{api_id}", headers=h)
    assert r.status_code in (200, 204)

    remaining = client.get("/api/registry/", headers=h).json()
    assert all(item["id"] != api_id for item in remaining)


def test_cannot_delete_other_users_api(client):
    h1 = _register_and_auth(client, "owner@test.com")
    h2 = _register_and_auth(client, "thief@test.com")
    _create_api(client, h1)
    api_id = client.get("/api/registry/", headers=h1).json()[0]["id"]

    r = client.delete(f"/api/registry/{api_id}", headers=h2)
    assert r.status_code in (403, 404)
