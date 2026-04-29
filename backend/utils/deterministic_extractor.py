"""
Deterministic extraction layer — extracts method, path, path/query params,
and body schema from an endpoint chunk WITHOUT calling an LLM.

The returned GroundTruth is used by SchemaAgent as authoritative anchors,
so the LLM cannot hallucinate method, path, or required path parameters.
"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class GroundTruth:
    method: str
    path: str
    path_params: list   # [{"name": "id", "type": "string", "required": True, "description": ""}]
    query_params: list
    headers: list
    body_schema: dict   # {} if not detected


def extract(chunk: dict) -> GroundTruth:
    """
    chunk keys: method, path, hint, content
    Returns GroundTruth with deterministically extracted structure.
    """
    method  = (chunk.get("method") or "GET").upper()
    path    = chunk.get("path") or "/"
    content = chunk.get("content") or ""

    try:
        data = json.loads(content)
        return _from_openapi(method, path, data)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    return _from_text(method, path, content)


# ── OpenAPI JSON ──────────────────────────────────────────────────────────────

def _from_openapi(method: str, path: str, data: dict) -> GroundTruth:
    """Extract from OpenAPI-format JSON chunk: {"/path": {"get": {operation}}}"""
    operation: dict = {}
    for path_item in data.values():
        if not isinstance(path_item, dict):
            continue
        for m_key, op in path_item.items():
            if isinstance(op, dict) and m_key.lower() == method.lower():
                operation = op
                break

    parameters = operation.get("parameters") or []
    path_params: list = []
    query_params: list = []
    headers: list = []

    for param in parameters:
        if not isinstance(param, dict):
            continue
        p_in   = (param.get("in") or "").lower()
        schema = param.get("schema") or {}
        p_type = schema.get("type") or param.get("type") or "string"
        p_req  = bool(param.get("required", p_in == "path"))
        entry = {
            "name":        param.get("name") or "",
            "type":        p_type,
            "required":    p_req,
            "description": param.get("description") or "",
        }
        if p_in == "path":
            path_params.append(entry)
        elif p_in == "query":
            query_params.append(entry)
        elif p_in == "header":
            headers.append(entry)

    # Guarantee every {token} in path is represented
    found_names = {p["name"] for p in path_params}
    for name in re.findall(r"\{(\w+)\}", path):
        if name not in found_names:
            path_params.append({"name": name, "type": "string", "required": True, "description": ""})
            found_names.add(name)

    # Extract body schema from requestBody
    body_schema: dict = {}
    rb_content = (operation.get("requestBody") or {}).get("content") or {}
    json_body  = rb_content.get("application/json") or {}
    body_schema = json_body.get("schema") or {}

    return GroundTruth(
        method=method,
        path=path,
        path_params=path_params,
        query_params=query_params,
        headers=headers,
        body_schema=body_schema,
    )


# ── Plain text / regex ────────────────────────────────────────────────────────

_SKIP_WORDS = {"get", "post", "put", "patch", "delete", "true", "false", "null", "none"}


def _from_text(method: str, path: str, content: str) -> GroundTruth:
    """Regex-based extraction from unstructured text."""
    path_params: list = [
        {"name": n, "type": "string", "required": True, "description": ""}
        for n in re.findall(r"\{(\w+)\}", path)
    ]
    path_names = {p["name"] for p in path_params}

    query_params: list = []
    seen: set = set()
    for m in re.finditer(r'(?:query[:\s]+|[?&])(\w+)', content, re.IGNORECASE):
        name = m.group(1)
        if name.lower() not in _SKIP_WORDS and name not in path_names and name not in seen:
            query_params.append({"name": name, "type": "string", "required": False, "description": ""})
            seen.add(name)

    headers: list = []
    seen_h: set = set()
    for m in re.finditer(r'\b(Authorization|Content-Type|Accept|X-[\w-]+)\b', content):
        hname = m.group(1)
        if hname not in seen_h:
            headers.append({"name": hname, "type": "string", "required": False, "description": ""})
            seen_h.add(hname)

    return GroundTruth(
        method=method,
        path=path,
        path_params=path_params,
        query_params=query_params,
        headers=headers,
        body_schema={},
    )
