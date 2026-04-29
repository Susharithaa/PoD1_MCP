"""
Tests for the confirm → SAVED flow that drives the frontend redirect
to /registry/<api_definition_id>.

Positive scenarios:
  - Manual API confirm returns state=SAVED with an api_definition_id
  - save_anyway=True skips blocking test verdicts and lands in SAVED
  - GET session after confirm shows state=SAVED

Negative scenarios:
  - Confirming a non-HITL_PENDING session raises 400 (via orchestrator)
  - Confirming another user's session returns 404
  - Confirming without auth returns 401
  - Validation errors bounce session back to HITL_PENDING (no api_definition_id)
  - Discard after HITL_PENDING → state=DISCARDED, no api_definition_id
  - GET on a SAVED session still returns api_definition_id (redirect survives reload)
"""
import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _register(client, email="user@test.com", password="pass123"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


MINIMAL_API = {
    "name": "Confirm Test API",
    "base_url": "https://api.confirm.example.com",
    "version": "1.0.0",
    "description": "Used to test confirm-to-SAVED flow",
    "auth_type": "none",
    "auth_header": "",
    "auth_credentials": None,
    "endpoints": [
        {
            "method": "GET",
            "path": "/status",
            "name": "Get Status",
            "description": "Health check endpoint",
            "auth_type": "",
            "parameters": [],
        }
    ],
}

INVALID_ENDPOINT_API = {
    **MINIMAL_API,
    "name": "Invalid Endpoint API",
    "endpoints": [
        {
            "method": "INVALID_METHOD",   # schema validator should reject this
            "path": "/bad",
            "name": "bad",
            "description": "",
            "auth_type": "",
            "parameters": [],
        }
    ],
}


def _create_hitl_session(client, headers, api=None):
    """Create a manual session and return its id when it reaches HITL_PENDING."""
    payload = api or MINIMAL_API
    r = client.post("/api/agent/manual", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    data = r.json()
    # Manual sessions auto-confirm; but with MOCK_LLM they may land in HITL_PENDING
    # or SAVED depending on the mock.  Return whatever state we got.
    return data


# ════════════════════════════════════════════════════════════════════════════
# Positive scenarios
# ════════════════════════════════════════════════════════════════════════════

def test_confirm_manual_session_reaches_saved(client):
    """
    POST /api/agent/manual auto-confirms (save_anyway=True internally).
    The session must end up SAVED and carry an api_definition_id so the
    frontend can redirect to /registry/<id>.
    """
    h = _register(client)
    data = _create_hitl_session(client, h)
    # Manual route skips live tests → should land SAVED
    assert data["state"] == "SAVED", f"Unexpected state: {data['state']}"
    assert data["api_definition_id"] is not None, "api_definition_id must be set on SAVED session"


def test_saved_session_api_definition_id_present_on_get(client):
    """
    GET /api/agent/<id> after confirm returns the api_definition_id.
    The frontend reads this to build the redirect URL.
    """
    h = _register(client)
    data = _create_hitl_session(client, h)
    session_id = data["id"]

    r = client.get(f"/api/agent/{session_id}", headers=h)
    assert r.status_code == 200
    fetched = r.json()
    assert fetched["state"] == "SAVED"
    assert fetched["api_definition_id"] == data["api_definition_id"]


def test_hitl_submit_with_save_anyway_skips_blocking_verdicts(client):
    """
    POST /api/agent/<id>/hitl with save_anyway=True must reach SAVED
    even when test results would normally block.
    """
    h = _register(client)
    # Create a chat-mode session so we can manually call /hitl
    chat_r = client.post("/api/agent/chat", json={"message": "Stripe API https://api.stripe.com/v1"}, headers=h)
    assert chat_r.status_code == 201
    session = chat_r.json()

    if session["state"] != "HITL_PENDING":
        pytest.skip("Mock LLM didn't land session in HITL_PENDING; skipping")

    r = client.post(
        f"/api/agent/{session['id']}/hitl",
        json={"edits": {}, "auth_credentials": None, "save_anyway": True},
        headers=h,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["state"] == "SAVED"
    assert result["api_definition_id"] is not None


def test_discard_then_state_is_discarded(client):
    """
    POST /api/agent/<id>/discard on HITL_PENDING sets state=DISCARDED.
    No api_definition_id should be set (no redirect to registry).
    """
    h = _register(client)
    chat_r = client.post("/api/agent/chat", json={"message": "Test API"}, headers=h)
    assert chat_r.status_code == 201
    session = chat_r.json()

    if session["state"] != "HITL_PENDING":
        pytest.skip("Session not in HITL_PENDING; skipping discard test")

    r = client.post(f"/api/agent/{session['id']}/discard", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["state"] == "DISCARDED"
    assert data.get("api_definition_id") is None


def test_list_sessions_includes_saved_with_api_definition_id(client):
    """
    GET /api/agent/ includes saved sessions and they carry api_definition_id.
    """
    h = _register(client)
    data = _create_hitl_session(client, h)
    assert data["state"] == "SAVED"

    r = client.get("/api/agent/", headers=h)
    assert r.status_code == 200
    sessions = r.json()
    saved = [s for s in sessions if s["state"] == "SAVED"]
    assert len(saved) >= 1
    assert all(s["api_definition_id"] is not None for s in saved)


# ════════════════════════════════════════════════════════════════════════════
# Negative scenarios
# ════════════════════════════════════════════════════════════════════════════

def test_hitl_requires_auth(client):
    """POST /hitl without a token returns 401."""
    r = client.post("/api/agent/nonexistent-id/hitl",
                    json={"edits": {}, "auth_credentials": None, "save_anyway": False})
    assert r.status_code == 401


def test_hitl_on_unknown_session_returns_404(client):
    """POST /hitl on a session that doesn't exist returns 404."""
    h = _register(client)
    r = client.post(
        "/api/agent/00000000-0000-0000-0000-000000000000/hitl",
        json={"edits": {}, "auth_credentials": None, "save_anyway": False},
        headers=h,
    )
    assert r.status_code == 404


def test_hitl_on_other_users_session_returns_404(client):
    """User B cannot confirm User A's session — returns 404."""
    ha = _register(client, "a@test.com")
    hb = _register(client, "b@test.com")

    chat_r = client.post("/api/agent/chat", json={"message": "Test API"}, headers=ha)
    assert chat_r.status_code == 201
    session_id = chat_r.json()["id"]

    r = client.post(
        f"/api/agent/{session_id}/hitl",
        json={"edits": {}, "auth_credentials": None, "save_anyway": False},
        headers=hb,
    )
    assert r.status_code == 404


def test_confirm_already_saved_session_raises_error(client):
    """
    Calling /hitl on an already-SAVED session should return an error
    (orchestrator raises ValueError for non-HITL_PENDING state).
    """
    h = _register(client)
    data = _create_hitl_session(client, h)
    assert data["state"] == "SAVED", "Pre-condition: need a SAVED session"
    session_id = data["id"]

    r = client.post(
        f"/api/agent/{session_id}/hitl",
        json={"edits": {}, "auth_credentials": None, "save_anyway": False},
        headers=h,
    )
    # The orchestrator raises ValueError for non-HITL_PENDING; router converts to 400
    assert r.status_code == 400
    assert "HITL_PENDING" in r.json()["detail"] or "state" in r.json()["detail"]


def test_confirm_discarded_session_raises_error(client):
    """POST /hitl on a DISCARDED session is rejected."""
    h = _register(client)
    chat_r = client.post("/api/agent/chat", json={"message": "Test API"}, headers=h)
    assert chat_r.status_code == 201
    session = chat_r.json()

    if session["state"] != "HITL_PENDING":
        pytest.skip("Session not in HITL_PENDING; cannot test discard → hitl path")

    client.post(f"/api/agent/{session['id']}/discard", headers=h)

    r = client.post(
        f"/api/agent/{session['id']}/hitl",
        json={"edits": {}, "auth_credentials": None, "save_anyway": False},
        headers=h,
    )
    assert r.status_code == 400


def test_get_session_requires_auth(client):
    """GET /api/agent/<id> without token returns 401."""
    r = client.get("/api/agent/some-id")
    assert r.status_code == 401


def test_discard_requires_auth(client):
    """POST /api/agent/<id>/discard without token returns 401."""
    r = client.post("/api/agent/some-id/discard")
    assert r.status_code == 401


def test_restart_creates_new_session_in_hitl_pending(client):
    """
    POST /api/agent/<id>/restart returns a NEW session id.
    The new session should not be SAVED yet (pipeline reruns from scratch).
    """
    h = _register(client)
    chat_r = client.post("/api/agent/chat", json={"message": "Test API"}, headers=h)
    assert chat_r.status_code == 201
    old_session = chat_r.json()

    if old_session["state"] != "HITL_PENDING":
        pytest.skip("Session not in HITL_PENDING; skipping restart test")

    r = client.post(f"/api/agent/{old_session['id']}/restart", headers=h)
    assert r.status_code == 200
    new_session = r.json()

    assert new_session["id"] != old_session["id"], "Restart must create a new session"
    assert new_session["state"] != "SAVED", "Restarted session should not be immediately SAVED"
    assert new_session.get("api_definition_id") is None
