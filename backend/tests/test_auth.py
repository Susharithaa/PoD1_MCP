"""Tests: auth register / login / me / RBAC / admin routes."""
import pytest


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_returns_token(client):
    r = client.post("/api/auth/register", json={
        "email": "user@test.com",
        "password": "pass1234",
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_first_user_is_admin(client):
    r = client.post("/api/auth/register", json={"email": "first@test.com", "password": "pass"})
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "admin"


def test_second_user_is_not_admin(client):
    client.post("/api/auth/register", json={"email": "first@test.com", "password": "pass"})
    r = client.post("/api/auth/register", json={"email": "second@test.com", "password": "pass"})
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "user"


def test_duplicate_email_rejected(client):
    client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass"})
    r = client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass"})
    assert r.status_code == 400


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(client):
    client.post("/api/auth/register", json={"email": "u@test.com", "password": "pass1234"})
    r = client.post("/api/auth/login", json={"email": "u@test.com", "password": "pass1234"})
    assert r.status_code == 200
    assert r.json()["status"] == "otp_required"
    assert r.json()["email"] == "u@test.com"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "u@test.com", "password": "correct"})
    r = client.post("/api/auth/login", json={"email": "u@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "x"})
    assert r.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────

def test_me_returns_user(client, registered_user):
    token, user = registered_user
    assert user["email"] == "admin@test.com"
    assert user["role"] == "admin"
    assert user["is_active"] is True


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_rejects_bad_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.here"})
    assert r.status_code == 401


# ── Admin routes ──────────────────────────────────────────────────────────────

def test_admin_list_users(admin_client):
    c, _ = admin_client
    r = c.get("/api/auth/admin/users")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_non_admin_cannot_list_users(client):
    # Register admin first, then a regular user
    client.post("/api/auth/register", json={"email": "admin@test.com", "password": "pass"})
    r = client.post("/api/auth/register", json={"email": "user@test.com", "password": "pass"})
    token = r.json()["access_token"]
    r2 = client.get("/api/auth/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 403


def test_admin_promote_user(admin_client, client):
    c, admin = admin_client
    # Register a second user
    r = client.post("/api/auth/register", json={"email": "user2@test.com", "password": "pass"})
    token2 = r.json()["access_token"]
    user2_id = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"}).json()["id"]

    # Admin promotes user2
    r2 = c.patch(f"/api/auth/admin/users/{user2_id}/role", json={"role": "admin"})
    assert r2.status_code == 200
    assert r2.json()["role"] == "admin"


def test_admin_cannot_demote_self(admin_client):
    c, admin = admin_client
    r = c.patch(f"/api/auth/admin/users/{admin['id']}/role", json={"role": "user"})
    assert r.status_code == 400


def test_admin_deactivate_user(admin_client, client):
    c, _ = admin_client
    r = client.post("/api/auth/register", json={"email": "victim@test.com", "password": "pass"})
    uid = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()["id"]

    r2 = c.patch(f"/api/auth/admin/users/{uid}/active", json={"is_active": False})
    assert r2.status_code == 200
    assert r2.json()["is_active"] is False


def test_deactivated_user_cannot_login(admin_client, client):
    c, _ = admin_client
    client.post("/api/auth/register", json={"email": "bye@test.com", "password": "pass"})
    # find user id via admin list
    uid = next(u["id"] for u in c.get("/api/auth/admin/users").json() if u["email"] == "bye@test.com")
    c.patch(f"/api/auth/admin/users/{uid}/active", json={"is_active": False})
    r = client.post("/api/auth/login", json={"email": "bye@test.com", "password": "pass"})
    assert r.status_code == 403


def test_admin_cannot_deactivate_self(admin_client):
    c, admin = admin_client
    r = c.patch(f"/api/auth/admin/users/{admin['id']}/active", json={"is_active": False})
    assert r.status_code == 400
