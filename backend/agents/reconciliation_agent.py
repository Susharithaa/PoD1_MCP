"""
ReconciliationAgent — post-SchemaAgent consistency pass.

Runs two layers:
  1. Deterministic: deduplication, auth_type alignment, naming convention check.
  2. LLM (small APIs only): cross-endpoint naming and schema coherence fix.
"""

import json
import re
from collections import Counter
from agents.base import BaseAgent
from models.agent_session import AgentSession
from llm.client import chat_json

_LLM_MAX_ENDPOINTS = 20   # only send to LLM if the API is small enough

_RECONCILE_SYSTEM = """You are an API schema consistency reviewer.
Given a list of API endpoints, fix naming and schema inconsistencies.

Fix only:
1. Parameter naming: pick one convention (snake_case preferred) and apply consistently.
2. auth_type: align with the api_auth_type unless an endpoint explicitly differs.
3. Duplicate or contradictory descriptions for the same concept.

Return {"endpoints": [...]} with ALL endpoints, preserving every field.
Only change what is inconsistent. Do NOT add, remove, or reorder endpoints.
Return ONLY the JSON object."""


class ReconciliationAgent(BaseAgent):
    name = "reconciliation_agent"

    async def run(self, session: AgentSession) -> AgentSession:
        draft     = session.draft_api or {}
        endpoints = list(draft.get("endpoints") or [])

        if not endpoints:
            return session

        # ── Pass 1: deterministic fixes ───────────────────────────────────────
        endpoints = _deduplicate(endpoints)
        endpoints = _align_auth(endpoints, draft.get("auth_type", "NONE"))
        endpoints = _normalise_names(endpoints)

        # ── Pass 2: LLM coherence (small APIs only) ───────────────────────────
        if len(endpoints) <= _LLM_MAX_ENDPOINTS:
            endpoints = await _llm_reconcile(endpoints, draft.get("auth_type", "NONE"))

        session.draft_api = {**draft, "endpoints": endpoints}
        return session


# ── Deterministic passes ──────────────────────────────────────────────────────

def _deduplicate(endpoints: list) -> list:
    """Remove exact method+path duplicates, keeping the first occurrence."""
    seen: set = set()
    out: list = []
    for ep in endpoints:
        key = (ep.get("method", "").upper(), ep.get("path", ""))
        if key not in seen:
            seen.add(key)
            out.append(ep)
    return out


def _align_auth(endpoints: list, api_auth: str) -> list:
    """
    If an endpoint's auth_type is empty/UNKNOWN, inherit the API-level auth_type.
    Never override an endpoint that explicitly sets a different valid auth.
    """
    valid = {"BEARER", "API_KEY", "BASIC", "OAUTH2", "NONE"}
    for ep in endpoints:
        current = (ep.get("auth_type") or "").upper()
        if current not in valid or current in ("", "UNKNOWN"):
            ep["auth_type"] = api_auth
    return endpoints


def _normalise_names(endpoints: list) -> list:
    """
    Detect and fix mixed camelCase/snake_case parameter names within the same API.
    Majority convention wins; minority params get renamed.
    """
    # Collect all parameter names
    all_names: list = []
    for ep in endpoints:
        props = (ep.get("input_schema") or {}).get("properties") or {}
        all_names.extend(props.keys())

    if not all_names:
        return endpoints

    snake_count = sum(1 for n in all_names if "_" in n)
    camel_count = sum(1 for n in all_names if re.search(r"[a-z][A-Z]", n))

    # Only rename if there's a clear majority and both styles present
    if snake_count == 0 or camel_count == 0:
        return endpoints

    use_snake = snake_count >= camel_count

    for ep in endpoints:
        in_schema = ep.get("input_schema") or {}
        props     = in_schema.get("properties") or {}
        required  = list(in_schema.get("required") or [])
        if not props:
            continue

        new_props: dict = {}
        new_required: list = []
        for name, val in props.items():
            new_name = _to_snake(name) if use_snake else name
            new_props[new_name] = val
            if name in required:
                new_required.append(new_name)

        ep["input_schema"] = {
            **in_schema,
            "properties": new_props,
            "required":   new_required,
        }
    return endpoints


def _to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ── LLM pass ─────────────────────────────────────────────────────────────────

async def _llm_reconcile(endpoints: list, api_auth: str) -> list:
    prompt = json.dumps({
        "api_auth_type": api_auth,
        "endpoints":     endpoints,
    }, indent=2)

    try:
        result = await chat_json(
            _RECONCILE_SYSTEM,
            prompt[:20_000],
            max_tokens=4096,
        )
        reconciled = result.get("endpoints")
        if isinstance(reconciled, list) and len(reconciled) == len(endpoints):
            # Ground truth anchor: never let LLM change method or path
            for orig, rec in zip(endpoints, reconciled):
                rec["method"] = orig["method"]
                rec["path"]   = orig["path"]
            return reconciled
    except Exception:
        pass  # LLM reconcile is best-effort

    return endpoints
