"""
Test setup:
- DATABASE_URL=sqlite:///:memory: with StaticPool so all connections share
  the same in-memory DB within a process.
- Tables dropped/created around each test for full isolation.
- Rate limiter storage reset between tests.
"""
import os
os.environ["DATABASE_URL"]    = "sqlite:///:memory:"
os.environ["JWT_SECRET"]      = "test-secret-key"
os.environ["MOCK_LLM"]        = "true"
os.environ["OPENAI_API_KEY"]  = "mock"
os.environ["ENCRYPTION_KEY"]  = "test-encryption-key-for-tests"

import pytest
from fastapi.testclient import TestClient

# Import after env vars are set
from database import Base, engine, get_db, init_db
from main import app


# ── Rate limiter reset ────────────────────────────────────────────────────────

def _reset_limiter():
    try:
        from utils.limiter import limiter
        storage = getattr(limiter, '_storage', None)
        if storage is not None:
            if hasattr(storage, 'reset'):
                storage.reset()
            elif hasattr(storage, 'storage') and isinstance(storage.storage, dict):
                storage.storage.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _isolate(request):
    """Fresh tables + clear rate limiter for every test."""
    # Import all models so metadata is populated
    from models import agent_session, api_definition, auth_config, chatgpt_connection, user  # noqa

    _reset_limiter()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    _reset_limiter()
    Base.metadata.drop_all(bind=engine)


# ── TestClient ────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(_isolate):
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Convenience fixtures ──────────────────────────────────────────────────────

@pytest.fixture()
def registered_user(client):
    """Register first user (auto-admin). Returns (token, user_dict)."""
    r = client.post("/api/auth/register", json={
        "email": "admin@test.com",
        "password": "password123",
        "full_name": "Test Admin",
    })
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return token, me


@pytest.fixture()
def admin_client(client, registered_user):
    """Client with admin Authorization header pre-set."""
    token, user = registered_user
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, user
