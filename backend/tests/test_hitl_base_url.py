"""
Tests: base_url edit via HITL is applied to the live test run and saved to final_api.

Core bug this covers:
  When the user edits base_url on the Review & Validate page and clicks "Try Again",
  the orchestrator must use the NEW base_url (from the HITL edits), not the original
  one from draft_api.  The test agent reads session.final_api, which is the merged
  result of draft_api + human_edits, so if _merge_edits is correct the right URL will
  be tested.

Positive:
  - base_url edit is reflected in final_api after HITL submit
  - save_anyway with updated base_url → final_api carries the new base_url into SAVED

Negative:
  - Submitting HITL with empty base_url returns validation error (bounces HITL_PENDING)
  - Submitting HITL with non-http base_url returns validation error
  - base_url from original draft_api is NOT used when edits override it
"""
import pytest
from unittest.mock import AsyncMock, patch


# ── helpers ───────────────────────────────────────────────────────────────────

def _register(client, email="url@test.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "pass123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


DRAFT_API = {
    "name": "Test API",
    "base_url": "https://OLD.example.com",
    "version": "1.0.0",
    "description": "Original draft",
    "auth_type": "none",
    "auth_header": "",
    "auth_credentials": None,
    "endpoints": [
        {
            "method": "GET",
            "path": "/ping",
            "name": "Ping",
            "description": "Health check",
            "auth_type": "",
            "parameters": [],
        }
    ],
}


def _create_session_in_hitl_pending(db, user_id, base_url="https://OLD.example.com"):
    """Directly insert a session in HITL_PENDING state so we can test HITL submit."""
    from models.agent_session import AgentSession
    import uuid
    draft = {
        "name": "Test API",
        "base_url": base_url,
        "version": "1.0.0",
        "description": "Draft",
        "auth_type": "none",
        "endpoints": [
            {"method": "GET", "path": "/ping", "name": "Ping",
             "description": "", "auth_type": "none", "input_schema": {"type": "object", "properties": {}}},
        ],
    }
    s = AgentSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        state="HITL_PENDING",
        mode="DOC",
        draft_api=draft,
        confidence_map={},
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _get_db():
    from database import SessionLocal
    return SessionLocal()


def _get_user_id(client, h):
    return client.get("/api/auth/me", headers=h).json()["id"]


# ════════════════════════════════════════════════════════════════════════════
# Positive: edited base_url is merged into final_api
# ════════════════════════════════════════════════════════════════════════════

def test_hitl_edit_base_url_reflected_in_final_api(client):
    """
    When the user submits HITL with a new base_url, session.final_api must
    carry the new base_url — not the stale draft_api one.
    """
    h = _register(client)
    user_id = _get_user_id(client, h)
    db = _get_db()
    session = _create_session_in_hitl_pending(db, user_id, base_url="https://OLD.example.com")
    db.close()

    new_base_url = "https://NEW.example.com"
    edits = {
        "name": "Test API",
        "base_url": new_base_url,
        "version": "1.0.0",
        "description": "Draft",
        "auth_type": "none",
        "endpoints": [
            {"method": "GET", "path": "/ping", "name": "Ping",
             "description": "", "auth_type": "none",
             "input_schema": {"type": "object", "properties": {}}},
        ],
    }

    # Patch API test agent so we don't make real HTTP calls
    with patch("agents.api_test_agent.ApiTestAgent.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = None

        r = client.post(
            f"/api/agent/{session.id}/hitl",
            json={"edits": edits, "auth_credentials": None, "save_anyway": True},
            headers=h,
        )

    assert r.status_code == 200, r.text
    result = r.json()
    # final_api (or draft_api if validation bounced) must have the new base_url
    final = result.get("final_api") or result.get("draft_api") or {}
    assert final.get("base_url") == new_base_url, (
        f"Expected final_api.base_url={new_base_url!r}, got {final.get('base_url')!r}"
    )


def test_hitl_save_anyway_with_new_base_url_reaches_saved(client):
    """save_anyway=True with a corrected base_url lands the session in SAVED."""
    h = _register(client, "save@test.com")
    user_id = _get_user_id(client, h)
    db = _get_db()
    session = _create_session_in_hitl_pending(db, user_id, base_url="https://OLD.example.com")
    db.close()

    edits = {
        "name": "Test API",
        "base_url": "https://FIXED.example.com",
        "version": "1.0.0",
        "description": "Fixed",
        "auth_type": "none",
        "endpoints": [
            {"method": "GET", "path": "/ping", "name": "Ping",
             "description": "", "auth_type": "none",
             "input_schema": {"type": "object", "properties": {}}},
        ],
    }

    with patch("agents.api_test_agent.ApiTestAgent.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = None

        r = client.post(
            f"/api/agent/{session.id}/hitl",
            json={"edits": edits, "auth_credentials": None, "save_anyway": True},
            headers=h,
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["state"] == "SAVED"
    assert data["api_definition_id"] is not None


def test_draft_base_url_not_used_when_edits_provide_new_one(client):
    """
    The original draft_api.base_url must NOT bleed through into final_api
    when the HITL edits include a new base_url.
    """
    h = _register(client, "bleed@test.com")
    user_id = _get_user_id(client, h)
    db = _get_db()
    session = _create_session_in_hitl_pending(db, user_id, base_url="https://ORIGINAL.example.com")
    db.close()

    edits = {
        "name": "Test API",
        "base_url": "https://REPLACED.example.com",
        "version": "1.0.0",
        "description": "Draft",
        "auth_type": "none",
        "endpoints": [
            {"method": "GET", "path": "/ping", "name": "Ping",
             "description": "", "auth_type": "none",
             "input_schema": {"type": "object", "properties": {}}},
        ],
    }

    with patch("agents.api_test_agent.ApiTestAgent.run", new_callable=AsyncMock):
        r = client.post(
            f"/api/agent/{session.id}/hitl",
            json={"edits": edits, "auth_credentials": None, "save_anyway": True},
            headers=h,
        )

    assert r.status_code == 200
    final = r.json().get("final_api") or r.json().get("draft_api") or {}
    assert "ORIGINAL" not in final.get("base_url", ""), (
        "Old base_url must not appear in final_api after HITL edit"
    )
    assert "REPLACED" in final.get("base_url", "")


# ════════════════════════════════════════════════════════════════════════════
# Negative: validation rejects bad base_url, session bounces to HITL_PENDING
# ════════════════════════════════════════════════════════════════════════════

def test_hitl_empty_base_url_bounces_to_hitl_pending(client):
    """
    Submitting HITL with an empty base_url fails schema validation.
    Session must return to HITL_PENDING with validation_errors set.
    """
    h = _register(client, "empty@test.com")
    user_id = _get_user_id(client, h)
    db = _get_db()
    session = _create_session_in_hitl_pending(db, user_id)
    db.close()

    edits = {
        "name": "Test API",
        "base_url": "",          # invalid — empty
        "version": "1.0.0",
        "description": "Draft",
        "auth_type": "none",
        "endpoints": [
            {"method": "GET", "path": "/ping", "name": "Ping",
             "description": "", "auth_type": "none",
             "input_schema": {"type": "object", "properties": {}}},
        ],
    }

    r = client.post(
        f"/api/agent/{session.id}/hitl",
        json={"edits": edits, "auth_credentials": None, "save_anyway": False},
        headers=h,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["state"] == "HITL_PENDING", f"Expected HITL_PENDING, got {data['state']}"
    assert data["validation_errors"], "Empty base_url must produce validation_errors"
    assert any("base_url" in e.lower() for e in data["validation_errors"])


def test_hitl_non_http_base_url_bounces_to_hitl_pending(client):
    """
    base_url without http:// or https:// must fail validation.
    """
    h = _register(client, "badurl@test.com")
    user_id = _get_user_id(client, h)
    db = _get_db()
    session = _create_session_in_hitl_pending(db, user_id)
    db.close()

    edits = {
        "name": "Test API",
        "base_url": "ftp://not-a-web-api.example.com",   # not http/https
        "version": "1.0.0",
        "description": "Draft",
        "auth_type": "none",
        "endpoints": [
            {"method": "GET", "path": "/ping", "name": "Ping",
             "description": "", "auth_type": "none",
             "input_schema": {"type": "object", "properties": {}}},
        ],
    }

    r = client.post(
        f"/api/agent/{session.id}/hitl",
        json={"edits": edits, "auth_credentials": None, "save_anyway": False},
        headers=h,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["state"] == "HITL_PENDING"
    assert data["validation_errors"]
    assert any("base_url" in e.lower() or "http" in e.lower() for e in data["validation_errors"])


def test_hitl_base_url_edit_requires_auth(client):
    """HITL submit without a token returns 401 regardless of payload."""
    r = client.post(
        "/api/agent/some-session-id/hitl",
        json={"edits": {"base_url": "https://new.example.com"}, "auth_credentials": None, "save_anyway": False},
    )
    assert r.status_code == 401


def test_hitl_base_url_edit_wrong_user_returns_404(client):
    """User B cannot edit User A's session even with a valid token."""
    ha = _register(client, "owner@test.com")
    hb = _register(client, "intruder@test.com")

    user_id_a = _get_user_id(client, ha)
    db = _get_db()
    session = _create_session_in_hitl_pending(db, user_id_a)
    db.close()

    r = client.post(
        f"/api/agent/{session.id}/hitl",
        json={"edits": {"base_url": "https://evil.example.com"}, "auth_credentials": None, "save_anyway": False},
        headers=hb,
    )
    assert r.status_code == 404
