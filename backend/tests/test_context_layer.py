"""
Corner cases for ContextLayer — session lifecycle, history building,
system prompt, context trimming, expiry.
"""
import os
os.environ.setdefault("DATABASE_URL",   "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET",     "test-secret")
os.environ.setdefault("MOCK_LLM",       "true")
os.environ.setdefault("OPENAI_API_KEY", "mock")
os.environ.setdefault("ENCRYPTION_KEY", "test-key")

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from context.context_layer import ContextLayer, _MAX_HISTORY_TURNS


def _make_api(name="Weather API", base_url="https://api.weather.com", endpoints=None):
    api = MagicMock()
    api.name     = name
    api.base_url = base_url
    ep = MagicMock()
    ep.name = endpoints[0] if endpoints else "Get Weather"
    ep.path = "/weather"
    api.endpoints = [ep]
    return api


# ── Session creation ──────────────────────────────────────────────────────────

def test_new_session_created_when_none_provided():
    cl = ContextLayer()
    sid, msgs = cl.build_messages(None, "hello", [], "u@test.com")
    assert sid is not None
    assert len(sid) == 36  # uuid4


def test_same_session_reused_on_second_call():
    cl = ContextLayer()
    sid1, _ = cl.build_messages(None, "hello", [], "u@test.com")
    sid2, _ = cl.build_messages(sid1, "follow-up", [], "u@test.com")
    assert sid1 == sid2


def test_unknown_session_id_creates_new_session():
    cl = ContextLayer()
    sid, _ = cl.build_messages("nonexistent-id", "hello", [], "u@test.com")
    assert sid != "nonexistent-id"


def test_expired_session_creates_new_session():
    cl = ContextLayer()
    sid1, _ = cl.build_messages(None, "hello", [], "u@test.com")

    # Force expiry
    cl._sessions[sid1].last_active = datetime.now(timezone.utc) - timedelta(hours=3)

    sid2, _ = cl.build_messages(sid1, "follow-up", [], "u@test.com")
    assert sid2 != sid1


def test_clear_session_removes_it():
    cl = ContextLayer()
    sid, _ = cl.build_messages(None, "hello", [], "u@test.com")
    cl.clear_session(sid)
    assert cl.session_info(sid) is None


def test_clear_nonexistent_session_is_safe():
    cl = ContextLayer()
    cl.clear_session("does-not-exist")  # should not raise


# ── Message structure ─────────────────────────────────────────────────────────

def test_messages_start_with_system_prompt():
    cl = ContextLayer()
    _, msgs = cl.build_messages(None, "hello", [], "u@test.com")
    assert msgs[0]["role"] == "system"
    assert "u@test.com" in msgs[0]["content"]


def test_user_message_is_last():
    cl = ContextLayer()
    _, msgs = cl.build_messages(None, "my question", [], "u@test.com")
    assert msgs[-1] == {"role": "user", "content": "my question"}


def test_connected_apis_appear_in_system_prompt():
    cl  = ContextLayer()
    api = _make_api("MyAPI", "https://myapi.com", ["Search"])
    _, msgs = cl.build_messages(None, "hi", [api], "u@test.com")
    system = msgs[0]["content"]
    assert "MyAPI" in system
    assert "https://myapi.com" in system


def test_no_apis_shows_none_in_prompt():
    cl = ContextLayer()
    _, msgs = cl.build_messages(None, "hi", [], "u@test.com")
    assert "none connected" in msgs[0]["content"].lower()


# ── History injection ─────────────────────────────────────────────────────────

def test_history_injected_between_system_and_user():
    cl  = ContextLayer()
    sid, _ = cl.build_messages(None, "turn 1", [], "u@test.com")

    cl.save_turn(sid, "turn 1", [{"role": "assistant", "content": "answer 1"}])

    _, msgs = cl.build_messages(sid, "turn 2", [], "u@test.com")
    roles = [m["role"] for m in msgs]
    # system → (history: user, assistant) → user
    assert roles == ["system", "user", "assistant", "user"]
    assert msgs[-1]["content"] == "turn 2"


def test_tool_call_sequence_preserved_in_history():
    """OpenAI requires: assistant(tool_calls) → tool → assistant(final)"""
    cl  = ContextLayer()
    sid, _ = cl.build_messages(None, "q", [], "u@test.com")

    turn = [
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function",
            "function": {"name": "t_abc", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": '{"temp": 18}'},
        {"role": "assistant", "content": "It is 18°C"},
    ]
    cl.save_turn(sid, "q", turn)

    _, msgs = cl.build_messages(sid, "follow-up", [], "u@test.com")
    history_roles = [m["role"] for m in msgs[1:-1]]
    assert history_roles == ["user", "assistant", "tool", "assistant"]


def test_history_trimmed_at_max_turns():
    cl  = ContextLayer()
    sid, _ = cl.build_messages(None, "q0", [], "u@test.com")

    # Fill beyond limit
    for i in range(_MAX_HISTORY_TURNS + 5):
        cl.save_turn(sid, f"q{i}", [{"role": "assistant", "content": f"a{i}"}])

    _, msgs = cl.build_messages(sid, "final", [], "u@test.com")
    # system + trimmed history + user — should not exceed sensible bound
    assert len(msgs) <= (_MAX_HISTORY_TURNS * 3) + 2


# ── session_info ─────────────────────────────────────────────────────────────

def test_session_info_returns_correct_turn_count():
    cl  = ContextLayer()
    sid, _ = cl.build_messages(None, "q1", [], "u@test.com")
    cl.save_turn(sid, "q1", [{"role": "assistant", "content": "a1"}])
    cl.build_messages(sid, "q2", [], "u@test.com")
    cl.save_turn(sid, "q2", [{"role": "assistant", "content": "a2"}])

    info = cl.session_info(sid)
    assert info["turns"] == 2


def test_session_info_none_for_missing():
    cl = ContextLayer()
    assert cl.session_info("bogus") is None
