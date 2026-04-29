"""
ApiTestAgent — live-tests each endpoint before the API is saved as an MCP tool.

Strategy
--------
- GET endpoints with no auth: make a real HTTP call with generated test params.
- Auth-required endpoints:    skip the call, set verdict SKIPPED (auth not available).
- POST / PUT / PATCH:         skip to avoid side effects; flag for manual testing.
- DELETE:                     always skip.
- Uses LLM to assess whether the response matches the declared schema.
- Results are informational — they never block saving.
"""

import re
import time
import json
import logging
import httpx

# Suppress SSL unverified-request noise from httpx internals
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

from agents.base import BaseAgent
from utils.encryption import decrypt_creds
from models.agent_session import AgentSession
from llm.client import chat_json


_SYSTEM = """You are an API testing expert. You are given details of an HTTP call made to
a real API and must assess whether it is working correctly.

Evaluate:
1. Whether the HTTP status code indicates success or a known error.
2. Whether the response body looks like it matches the described schema.
3. Any obvious issues (wrong content type, error message in body, etc.).

Return ONLY a JSON object — no markdown:
{
  "verdict":    "PASS" | "AUTH_REQUIRED" | "WARNING" | "UNREACHABLE",
  "assessment": "One sentence summary",
  "issues":     ["issue1", ...]
}

Verdict rules:
  PASS          — 2xx status, response body looks correct.
  AUTH_REQUIRED — 401 or 403 status (expected when no credentials provided).
  WARNING       — reachable but unexpected status / body mismatch.
  UNREACHABLE   — connection refused, timeout, DNS failure.
"""


# ── Test-parameter generator ──────────────────────────────────────────────────

_NAME_HINTS: dict[str, object] = {
    "latitude":    51.5,    "lat":        51.5,
    "longitude":  -0.13,   "lon":        -0.13,   "lng":    -0.13,
    "city":       "London", "country":   "GB",
    "id":         "1",      "user_id":   "1",      "item_id": "1",
    "page":        1,       "limit":      10,       "offset":  0,
    "size":        10,      "count":      10,
    "start_date": "2024-01-01", "end_date": "2024-01-31",
    "date":       "2024-01-15",
    "query":      "test",   "q":          "test",
    "name":       "test",   "email":      "test@example.com",
    "current_weather": True, "hourly":   False,
}

_TYPE_DEFAULTS: dict[str, object] = {
    "string":  "test",
    "number":  1.0,
    "integer": 1,
    "boolean": True,
}


def _generate_params(input_schema: dict | None) -> dict:
    if not input_schema or not input_schema.get("properties"):
        return {}
    required = set(input_schema.get("required") or [])
    params: dict = {}
    for name, prop in input_schema["properties"].items():
        if required and name not in required:
            continue                          # only required params in test
        ptype = prop.get("type", "string")
        if ptype in ("object", "array"):
            continue                          # skip complex types

        # prefer name-hint, fall back to type default
        key = next((k for k in _NAME_HINTS if k in name.lower()), None)
        params[name] = _NAME_HINTS[key] if key else _TYPE_DEFAULTS.get(ptype, "test")
    return params


def _substitute_path(path: str, params: dict) -> tuple[str, dict]:
    """Replace {param} tokens in path, return (resolved_path, remaining_params)."""
    remaining = dict(params)
    for token in re.findall(r"\{(\w+)\}", path):
        if token in remaining:
            path = path.replace(f"{{{token}}}", str(remaining.pop(token)))
        else:
            path = path.replace(f"{{{token}}}", "1")   # fallback
    return path, remaining


# ── Agent ─────────────────────────────────────────────────────────────────────

class ApiTestAgent(BaseAgent):

    async def run(self, session: AgentSession) -> None:
        api = session.final_api or session.draft_api or {}
        base_url = (api.get("base_url") or "").rstrip("/")
        endpoints = api.get("endpoints") or []
        auth_store = decrypt_creds(session.auth_credentials) or {}

        results = []
        for i, ep in enumerate(endpoints):
            creds = _resolve_creds(auth_store, i)
            result = await self._test_one(base_url, ep, api.get("name", "API"), creds)
            results.append(result)

        session.api_test_results = results

    # ── per-endpoint test ──────────────────────────────────────────────────────

    async def _test_one(self, base_url: str, ep: dict, api_name: str, creds: dict | None = None) -> dict:
        name   = ep.get("name") or f"{ep.get('method','GET')} {ep.get('path','/')}"
        method = (ep.get("method") or "GET").upper()
        path   = ep.get("path") or "/"
        auth   = (ep.get("auth_type") or "").lower()

        base = {
            "endpoint_name": name,
            "method":        method,
            "path":          path,
            "verdict":       "SKIPPED",
            "assessment":    "",
            "issues":        [],
            "skipped":       True,
            "skip_reason":   None,
            "status_code":   None,
            "url_tested":    None,
            "test_params":   {},
            "response_preview": None,
            "duration_ms":   None,
            "error":         None,
        }

        # Skip non-GET (side-effect risk)
        if method != "GET":
            base["skip_reason"] = f"{method} endpoints are skipped to avoid unintended side effects"
            return base

        # Skip auth-required endpoints only when no credentials were provided
        cred_type = (creds or {}).get("type", "none")
        has_creds = bool(creds) and cred_type != "none"
        if auth and auth not in ("none", "") and not has_creds:
            base["skip_reason"] = f"Requires {auth.upper()} authentication — no credentials provided"
            base["verdict"]     = "AUTH_REQUIRED"
            return base

        if not base_url:
            base["skip_reason"] = "No base URL configured"
            return base

        # Build request
        params = _generate_params(ep.get("input_schema"))
        resolved_path, query_params = _substitute_path(path, params)
        url = f"{base_url}{resolved_path}"

        base["url_tested"]  = url + (f"?{_qs(query_params)}" if query_params else "")
        base["test_params"] = params
        base["skipped"]     = False

        # Make the call
        t0 = time.monotonic()
        try:
            req_auth, extra_headers, extra_params = _build_request_auth(creds)
            merged_params = {**query_params, **extra_params}
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(
                    url, params=merged_params,
                    auth=req_auth, headers=extra_headers,
                )
            duration = int((time.monotonic() - t0) * 1000)
            preview  = resp.text[:500]

            base["status_code"]      = resp.status_code
            base["response_preview"] = preview
            base["duration_ms"]      = duration

            # LLM assessment
            assessment = await self._assess(api_name, name, method, url, query_params,
                                            resp.status_code, preview)
            base.update(assessment)

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            base["verdict"]    = "UNREACHABLE"
            base["assessment"] = f"Could not reach {url}: {exc}"
            base["error"]      = str(exc)

        except Exception as exc:
            base["verdict"]    = "WARNING"
            base["assessment"] = f"Unexpected error during test: {exc}"
            base["error"]      = str(exc)

        return base

    # ── LLM call ──────────────────────────────────────────────────────────────

    async def _assess(self, api_name: str, ep_name: str, method: str,
                      url: str, params: dict, status_code: int, body: str) -> dict:
        user_msg = (
            f"API name: {api_name}\n"
            f"Endpoint: {ep_name}  ({method} {url})\n"
            f"Test params: {json.dumps(params)}\n"
            f"status_code: {status_code}\n"
            f"Response body (truncated): {body[:400]}"
        )
        try:
            result = await chat_json(_SYSTEM, user_msg, max_tokens=256)
            return {
                "verdict":    result.get("verdict", "WARNING"),
                "assessment": result.get("assessment", ""),
                "issues":     result.get("issues", []),
            }
        except Exception:
            # Don't fail the whole pipeline on LLM errors
            code = status_code or 0
            verdict = "PASS" if 200 <= code < 300 else "AUTH_REQUIRED" if code in (401, 403) else "WARNING"
            return {"verdict": verdict, "assessment": f"HTTP {code}", "issues": []}


def _qs(params: dict) -> str:
    return "&".join(f"{k}={v}" for k, v in params.items())


def _resolve_creds(auth_store: dict, index: int) -> dict | None:
    """Return the credentials dict for a given endpoint index."""
    if not auth_store:
        return None
    mode = auth_store.get("mode", "same")
    if mode == "per_endpoint":
        creds_list = auth_store.get("credentials", [])
        return creds_list[index] if index < len(creds_list) else None
    return auth_store  # "same" mode — same creds for every endpoint


def _build_request_auth(
    creds: dict | None,
) -> tuple[httpx.BasicAuth | None, dict, dict]:
    """
    Returns (httpx_auth, extra_headers, extra_query_params) for the given creds dict.
    Supports: basic, bearer, api_key (header), api_key_query, oauth2 (skipped — complex).
    """
    if not creds:
        return None, {}, {}

    ctype = (creds.get("type") or "none").lower()

    if ctype == "basic":
        return (
            httpx.BasicAuth(creds.get("username", ""), creds.get("password", "")),
            {}, {},
        )

    if ctype == "bearer":
        token = creds.get("token", "")
        return None, {"Authorization": f"Bearer {token}"}, {}

    if ctype == "api_key":
        header = creds.get("header_name", "X-API-Key")
        value  = creds.get("value", "")
        return None, {header: value}, {}

    if ctype == "api_key_query":
        param = creds.get("param_name", "api_key")
        value = creds.get("value", "")
        return None, {}, {param: value}

    # oauth2 and unknown: skip (too complex for automated test)
    return None, {}, {}
