"""
Tests for PATCH /api/agent/{id}/draft

Covers:
  - Endpoint deletion persists to session.draft_api
  - Refreshing form reads updated draft (no ghost endpoints)
  - 400 returned for sessions not in HITL_PENDING/FAILED
  - 404 returned for another user's session
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
from models.agent_session import AgentSession
from models.user import User
from utils.auth import create_access_token

# ── In-memory SQLite for tests ─────────────────────────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_patch_draft.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()  # release all connections before cleanup (Windows)
    import os
    try:
        if os.path.exists("./test_patch_draft.db"):
            os.remove("./test_patch_draft.db")
    except PermissionError:
        pass  # Windows may keep the handle open briefly; not critical


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _make_user(db, email="patchtest@example.com", role="user"):
    from uuid import uuid4
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"]).hash("password123")
    user = User(id=str(uuid4()), email=email, hashed_password=pwd,
                full_name="Patch Tester", role=role,
                chat_status="approved", credits=10.0)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_session(db, user_id, state="HITL_PENDING", draft=None):
    from uuid import uuid4
    s = AgentSession(
        id=str(uuid4()),
        user_id=user_id,
        state=state,
        mode="DOC",
        draft_api=draft or {
            "name": "Test API",
            "base_url": "https://api.test.com",
            "endpoints": [
                {"method": "GET",  "path": "/users",    "name": "list_users",   "auth_type": "NONE"},
                {"method": "POST", "path": "/users",    "name": "create_user",  "auth_type": "NONE"},
                {"method": "GET",  "path": "/users/{id}", "name": "get_user",   "auth_type": "NONE"},
            ],
        },
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def user_and_token():
    db = TestingSessionLocal()
    try:
        user = _make_user(db)
        token = create_access_token(user.id)
        return user, token
    finally:
        db.close()


@pytest.fixture(scope="module")
def other_user_token():
    db = TestingSessionLocal()
    try:
        user = _make_user(db, email="other@example.com")
        token = create_access_token(user.id)
        return token
    finally:
        db.close()


# ── Tests ──────────────────────────────────────────────────────────────────

def test_patch_draft_removes_endpoint(client, user_and_token):
    """Deleting an endpoint via PATCH persists to draft_api."""
    user, token = user_and_token
    db = TestingSessionLocal()
    session = _make_session(db, user.id)
    db.close()

    # Remove the POST /users endpoint
    updated_endpoints = [
        {"method": "GET",  "path": "/users",      "name": "list_users", "auth_type": "NONE"},
        {"method": "GET",  "path": "/users/{id}", "name": "get_user",   "auth_type": "NONE"},
    ]

    resp = client.patch(
        f"/api/agent/{session.id}/draft",
        json={"endpoints": updated_endpoints},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    saved_endpoints = data["draft_api"]["endpoints"]
    assert len(saved_endpoints) == 2
    paths = [e["path"] for e in saved_endpoints]
    assert "/users/{id}" in paths
    assert "/users" in paths
    # POST endpoint gone
    methods = [e["method"] for e in saved_endpoints if e["path"] == "/users"]
    assert "POST" not in methods


def test_patch_draft_persists_on_reload(client, user_and_token):
    """GET session after PATCH returns the updated draft (no ghost endpoints)."""
    user, token = user_and_token
    db = TestingSessionLocal()
    session = _make_session(db, user.id)
    db.close()

    # Delete one endpoint
    remaining = [
        {"method": "GET", "path": "/users", "name": "list_users", "auth_type": "NONE"},
    ]
    client.patch(
        f"/api/agent/{session.id}/draft",
        json={"endpoints": remaining},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Simulate page refresh — GET the session fresh
    get_resp = client.get(
        f"/api/agent/{session.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    reloaded = get_resp.json()["draft_api"]["endpoints"]
    assert len(reloaded) == 1
    assert reloaded[0]["path"] == "/users"
    assert reloaded[0]["method"] == "GET"


def test_patch_draft_preserves_other_fields(client, user_and_token):
    """PATCH only touches the keys provided; other draft_api fields are unchanged."""
    user, token = user_and_token
    db = TestingSessionLocal()
    session = _make_session(db, user.id, draft={
        "name": "My API",
        "base_url": "https://api.example.com",
        "version": "2.0.0",
        "endpoints": [
            {"method": "GET", "path": "/items", "name": "list_items", "auth_type": "NONE"},
        ],
    })
    db.close()

    resp = client.patch(
        f"/api/agent/{session.id}/draft",
        json={"endpoints": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    draft = resp.json()["draft_api"]
    assert draft["name"] == "My API"
    assert draft["base_url"] == "https://api.example.com"
    assert draft["version"] == "2.0.0"
    assert draft["endpoints"] == []


def test_patch_draft_blocked_on_saved_session(client, user_and_token):
    """PATCH returns 400 when session is already SAVED."""
    user, token = user_and_token
    db = TestingSessionLocal()
    session = _make_session(db, user.id, state="SAVED")
    db.close()

    resp = client.patch(
        f"/api/agent/{session.id}/draft",
        json={"endpoints": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "editable" in resp.json()["detail"].lower()


def test_patch_draft_blocked_on_discarded_session(client, user_and_token):
    """PATCH returns 400 when session is DISCARDED."""
    user, token = user_and_token
    db = TestingSessionLocal()
    session = _make_session(db, user.id, state="DISCARDED")
    db.close()

    resp = client.patch(
        f"/api/agent/{session.id}/draft",
        json={"endpoints": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_patch_draft_404_for_other_users_session(client, user_and_token, other_user_token):
    """PATCH returns 404 when a different user tries to access the session."""
    user, token = user_and_token
    db = TestingSessionLocal()
    session = _make_session(db, user.id)
    db.close()

    resp = client.patch(
        f"/api/agent/{session.id}/draft",
        json={"endpoints": []},
        headers={"Authorization": f"Bearer {other_user_token}"},
    )
    assert resp.status_code == 404


def test_patch_draft_allowed_on_failed_session(client, user_and_token):
    """PATCH is allowed on FAILED sessions so users can fix and retry."""
    user, token = user_and_token
    db = TestingSessionLocal()
    session = _make_session(db, user.id, state="FAILED")
    db.close()

    resp = client.patch(
        f"/api/agent/{session.id}/draft",
        json={"endpoints": [{"method": "GET", "path": "/fixed", "name": "fixed", "auth_type": "NONE"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["draft_api"]["endpoints"][0]["path"] == "/fixed"
