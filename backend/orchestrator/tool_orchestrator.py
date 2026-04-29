"""
Tool Orchestrator — sits between GPT-4o tool_calls and the actual HTTP execution.

Responsibilities:
  1. Execute independent tool calls in PARALLEL (asyncio.gather)
  2. Retry failed HTTP calls up to MAX_RETRIES times with exponential backoff
  3. Isolate failures — one bad tool does not block the others
  4. Return structured ExecutionResult objects for clean GPT-4o synthesis
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.orm import Session

from models.api_definition import ApiDefinition, ApiEndpoint
from translators.openai_translator import resolve_tool_call
from utils.encryption import decrypt_creds

MAX_RETRIES     = 2
RETRY_DELAY_S   = 0.5   # base delay; doubles each attempt
TOOL_TIMEOUT_S  = 15.0


@dataclass
class ExecutionResult:
    tool_call_id: str
    tool_name:    str
    api_name:     str
    endpoint:     str
    arguments:    dict
    result_text:  str
    success:      bool
    attempts:     int = 1
    skipped:      bool = False


class ToolOrchestrator:
    """
    Stateless — safe to instantiate once at module level and reuse.
    All state lives in the method call stack.
    """

    async def execute_all(
        self,
        tool_calls: list,
        db: Session,
    ) -> list[ExecutionResult]:
        """
        Dispatch all tool_calls from a single GPT-4o response in parallel.
        Returns one ExecutionResult per tool_call, in original order.
        """
        tasks = [self._execute_one(tc, db) for tc in tool_calls]
        return list(await asyncio.gather(*tasks))

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _execute_one(self, tc: Any, db: Session) -> ExecutionResult:
        tool_name = tc.function.name
        try:
            args = json.loads(tc.function.arguments)
        except Exception:
            args = {}

        api_obj, ep_obj = resolve_tool_call(tool_name, db)

        if not api_obj or not ep_obj:
            return ExecutionResult(
                tool_call_id=tc.id,
                tool_name=tool_name,
                api_name="unknown",
                endpoint=tool_name,
                arguments=args,
                result_text=json.dumps({
                    "status": "TOOL_NOT_FOUND",
                    "message": f"No registered endpoint matches tool '{tool_name}'.",
                }),
                success=False,
            )

        missing = _missing_required_params(ep_obj, args)
        if missing:
            return ExecutionResult(
                tool_call_id=tc.id,
                tool_name=tool_name,
                api_name=api_obj.name,
                endpoint=ep_obj.name or ep_obj.path,
                arguments=args,
                result_text=_missing_params_message(ep_obj, missing),
                success=False,
                skipped=True,
            )

        result_text, success, attempts = await self._execute_with_retry(api_obj, ep_obj, args)

        return ExecutionResult(
            tool_call_id=tc.id,
            tool_name=tool_name,
            api_name=api_obj.name,
            endpoint=ep_obj.name or ep_obj.path,
            arguments=args,
            result_text=result_text,
            success=success,
            attempts=attempts,
        )

    async def _execute_with_retry(
        self,
        api: ApiDefinition,
        ep: ApiEndpoint,
        arguments: dict,
    ) -> tuple[str, bool, int]:
        """Returns (result_text, success, attempts_used)."""
        last_error = ""
        for attempt in range(1, MAX_RETRIES + 2):  # attempts: 1, 2, 3
            result_text, success = await _http_call(api, ep, arguments)
            if success:
                return result_text, True, attempt
            last_error = result_text
            if attempt <= MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_S * (2 ** (attempt - 1)))

        return last_error, False, MAX_RETRIES + 1


# ── HTTP execution (shared with orchestrator) ─────────────────────────────────

async def _http_call(
    api: ApiDefinition,
    ep: ApiEndpoint,
    arguments: dict,
) -> tuple[str, bool]:
    if not api.base_url:
        return "Error: API has no base_url configured", False

    url  = f"{api.base_url.rstrip('/')}{ep.path}"
    args = dict(arguments)

    for param in re.findall(r"\{(\w+)\}", ep.path):
        if param in args:
            url = url.replace(f"{{{param}}}", str(args.pop(param)))

    req_auth, extra_headers, extra_params = _build_auth(decrypt_creds(ep.auth_credentials))
    if extra_params:
        args.update(extra_params)

    try:
        async with httpx.AsyncClient(timeout=TOOL_TIMEOUT_S, verify=False) as client:
            method = ep.method.upper()
            if method == "GET":
                resp = await client.get(url, params=args, auth=req_auth, headers=extra_headers)
            elif method == "DELETE":
                resp = await client.delete(url, params=args, auth=req_auth, headers=extra_headers)
            else:
                resp = await client.request(method, url, json=args, auth=req_auth, headers=extra_headers)
        return resp.text[:2000], resp.status_code < 400
    except Exception as exc:
        return f"Request failed: {exc}", False


def _build_auth(creds: dict | None) -> tuple:
    if not creds:
        return None, {}, {}
    ctype = (creds.get("type") or "none").lower()
    if ctype == "basic":
        return httpx.BasicAuth(creds.get("username", ""), creds.get("password", "")), {}, {}
    if ctype == "bearer":
        return None, {"Authorization": f"Bearer {creds.get('token', '')}"}, {}
    if ctype == "api_key":
        header = creds.get("header_name", "X-API-Key")
        return None, {header: creds.get("value", "")}, {}
    if ctype == "api_key_query":
        return None, {}, {creds.get("param_name", "api_key"): creds.get("value", "")}
    return None, {}, {}


def _missing_required_params(ep: ApiEndpoint, arguments: dict) -> list[str]:
    schema   = ep.input_schema or {}
    required = schema.get("required") or []
    return [p for p in required if p not in arguments or arguments[p] is None]


def _missing_params_message(ep: ApiEndpoint, missing: list[str]) -> str:
    schema  = ep.input_schema or {}
    props   = schema.get("properties") or {}
    details = []
    for name in missing:
        prop  = props.get(name, {})
        ptype = prop.get("type", "string")
        desc  = prop.get("description", "")
        entry = f'"{name}" ({ptype})'
        if desc:
            entry += f" — {desc}"
        details.append(entry)
    return json.dumps({
        "status":  "MISSING_REQUIRED_PARAMETERS",
        "tool":    ep.name,
        "missing": missing,
        "details": details,
        "message": (
            f"Cannot call '{ep.name}' — missing required parameters: "
            + ", ".join(missing)
            + ". Please ask the user to provide them."
        ),
    })


# Module-level singleton
tool_orchestrator = ToolOrchestrator()
