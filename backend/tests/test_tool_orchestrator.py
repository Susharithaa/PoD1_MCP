"""
Corner cases for ToolOrchestrator — parallel execution, retry,
partial failures, missing params, tool-not-found.
"""
import os
os.environ.setdefault("DATABASE_URL",   "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET",     "test-secret")
os.environ.setdefault("MOCK_LLM",       "true")
os.environ.setdefault("OPENAI_API_KEY", "mock")
os.environ.setdefault("ENCRYPTION_KEY", "test-key")

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from orchestrator.tool_orchestrator import ToolOrchestrator, _http_call


def _make_tool_call(name="t_abc_def", args=None, call_id="c1"):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name      = name
    tc.function.arguments = json.dumps(args or {})
    return tc


def _make_api_ep(method="GET", path="/weather", required=None, name="Get Weather"):
    api = MagicMock()
    api.name     = "Weather API"
    api.base_url = "https://api.example.com"

    ep = MagicMock()
    ep.name   = name
    ep.path   = path
    ep.method = method
    ep.input_schema = {
        "type": "object",
        "properties": {p: {"type": "string"} for p in (required or [])},
        "required": required or [],
    }
    ep.auth_credentials = None
    return api, ep


# ── Tool not found ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_not_found_returns_failure():
    orch = ToolOrchestrator()
    db   = MagicMock()

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(None, None)):
        results = await orch.execute_all([_make_tool_call("t_missing")], db)

    assert len(results) == 1
    r = results[0]
    assert not r.success
    payload = json.loads(r.result_text)
    assert payload["status"] == "TOOL_NOT_FOUND"


# ── Missing required params ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_required_params_skips_http():
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep(required=["city"])
    tc      = _make_tool_call(args={})  # city missing

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)):
        results = await orch.execute_all([tc], db)

    r = results[0]
    assert not r.success
    assert r.skipped
    payload = json.loads(r.result_text)
    assert payload["status"] == "MISSING_REQUIRED_PARAMETERS"
    assert "city" in payload["missing"]


# ── Successful single call ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_successful_single_tool_call():
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep()
    tc      = _make_tool_call(args={"q": "London"})

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call",
               new=AsyncMock(return_value=('{"temp": 18}', True))):
        results = await orch.execute_all([tc], db)

    assert results[0].success
    assert results[0].attempts == 1
    assert '{"temp": 18}' == results[0].result_text


# ── Parallel execution ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_parallel_execution_all_succeed():
    """Two independent tool calls should both complete."""
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep()

    tcs = [
        _make_tool_call(args={"city": "Tokyo"},  call_id="c1"),
        _make_tool_call(args={"city": "London"}, call_id="c2"),
    ]

    call_log = []

    async def fake_http(api, ep, args):
        call_log.append(args["city"])
        return (f'{{"city": "{args["city"]}"}}', True)

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call", side_effect=fake_http):
        results = await orch.execute_all(tcs, db)

    assert len(results) == 2
    assert all(r.success for r in results)
    assert set(call_log) == {"Tokyo", "London"}


@pytest.mark.asyncio
async def test_parallel_preserves_order():
    """Results are returned in the same order as input tool_calls."""
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep()

    tcs = [_make_tool_call(args={"n": str(i)}, call_id=f"c{i}") for i in range(4)]

    async def fake_http(api, ep, args):
        return (args["n"], True)

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call", side_effect=fake_http):
        results = await orch.execute_all(tcs, db)

    assert [r.result_text for r in results] == ["0", "1", "2", "3"]


# ── Partial failure isolation ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_one_failure_does_not_block_others():
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep()

    tcs = [
        _make_tool_call(args={"n": "ok"},   call_id="c1"),
        _make_tool_call(args={"n": "fail"}, call_id="c2"),
        _make_tool_call(args={"n": "ok2"},  call_id="c3"),
    ]

    async def fake_http(api, ep, args):
        if args["n"] == "fail":
            return ("network error", False)
        return (f"result_{args['n']}", True)

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call", side_effect=fake_http):
        results = await orch.execute_all(tcs, db)

    assert results[0].success  is True
    assert results[1].success  is False
    assert results[2].success  is True


# ── Retry logic ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep()
    tc      = _make_tool_call()

    attempt_count = {"n": 0}

    async def flaky_http(api, ep, args):
        attempt_count["n"] += 1
        if attempt_count["n"] < 2:
            return ("timeout", False)
        return ('{"ok": true}', True)

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call", side_effect=flaky_http), \
         patch("asyncio.sleep", new=AsyncMock()):  # skip real delay
        results = await orch.execute_all([tc], db)

    assert results[0].success  is True
    assert results[0].attempts == 2


@pytest.mark.asyncio
async def test_retry_exhausted_reports_failure():
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep()
    tc      = _make_tool_call()

    async def always_fail(api, ep, args):
        return ("connection refused", False)

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call", side_effect=always_fail), \
         patch("asyncio.sleep", new=AsyncMock()):
        results = await orch.execute_all([tc], db)

    assert results[0].success  is False
    assert results[0].attempts == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_no_retry_on_missing_params():
    """MISSING_REQUIRED_PARAMETERS should not trigger HTTP retries."""
    orch    = ToolOrchestrator()
    db      = MagicMock()
    api, ep = _make_api_ep(required=["city"])
    tc      = _make_tool_call(args={})

    http_calls = {"n": 0}

    async def counting_http(api, ep, args):
        http_calls["n"] += 1
        return ("ok", True)

    with patch("orchestrator.tool_orchestrator.resolve_tool_call", return_value=(api, ep)), \
         patch("orchestrator.tool_orchestrator._http_call", side_effect=counting_http):
        await orch.execute_all([tc], db)

    assert http_calls["n"] == 0  # never called


# ── Path param substitution ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_path_params_substituted():
    captured = {}

    async def fake_client_get(url, **kwargs):
        captured["url"] = url
        resp = MagicMock()
        resp.text        = '{"id": 42}'
        resp.status_code = 200
        return resp

    api, ep = _make_api_ep(path="/users/{user_id}")

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__  = AsyncMock(return_value=False)
        instance.get        = fake_client_get
        MockClient.return_value = instance

        result, success = await _http_call(api, ep, {"user_id": "99"})

    assert success
    assert "99" in captured["url"]
    assert "{user_id}" not in captured["url"]


# ── Empty tool_calls list ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_tool_calls_returns_empty_list():
    orch = ToolOrchestrator()
    db   = MagicMock()
    results = await orch.execute_all([], db)
    assert results == []
