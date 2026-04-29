"""
Smart chunker — splits API docs into per-endpoint chunks with no boundary overlap.

Option A (structured):  OpenAPI / Postman → chunk at object level
Option C (unstructured): PDF / TXT / DOCX → two-pass via LLM
"""

import json
import re
import asyncio
from dataclasses import dataclass, field

from llm.client import chat_json


@dataclass
class EndpointChunk:
    method: str
    path: str
    hint: str                      # human-readable label e.g. "POST /users"
    content: str                   # raw text/JSON for this endpoint only
    base_info: dict = field(default_factory=dict)  # name, base_url, auth_type


# ── Public entry point ────────────────────────────────────────────────────────

async def chunk(text: str, fmt: str) -> tuple[dict, list[EndpointChunk]]:
    """
    Returns (base_info, [EndpointChunk]).
    base_info has: name, base_url, auth_type, description (may be partial/empty)
    """
    if fmt == "openapi_json":
        return _chunk_openapi(text)
    if fmt == "postman":
        return _chunk_postman(text)
    # unstructured: Option C two-pass
    return await _chunk_unstructured(text)


# ── Option A: Structured formats ──────────────────────────────────────────────

def _chunk_openapi(text: str) -> tuple[dict, list[EndpointChunk]]:
    spec = json.loads(text)

    # Resolve base_url from servers or host+basePath
    base_url = ""
    if "servers" in spec and spec["servers"]:
        base_url = spec["servers"][0].get("url", "")
    elif "host" in spec:
        scheme = (spec.get("schemes") or ["https"])[0]
        base_url = f"{scheme}://{spec['host']}{spec.get('basePath', '')}"

    info = spec.get("info", {})
    base_info = {
        "name":        info.get("title", ""),
        "description": info.get("description", ""),
        "base_url":    base_url,
        "auth_type":   _detect_openapi_auth(spec),
    }

    # Collect global parameters for reuse
    global_params = spec.get("components", {}).get("parameters", {})

    chunks: list[EndpointChunk] = []
    for path, path_item in spec.get("paths", {}).items():
        path_level_params = path_item.get("parameters", [])
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            operation = path_item.get(method)
            if not operation:
                continue
            # Merge path-level params into operation
            op_copy = dict(operation)
            merged_params = list(path_level_params) + list(op_copy.get("parameters", []))
            if merged_params:
                op_copy["parameters"] = merged_params
            chunks.append(EndpointChunk(
                method=method.upper(),
                path=path,
                hint=f"{method.upper()} {path}",
                content=json.dumps({path: {method: op_copy}}, indent=2),
                base_info=base_info,
            ))
    return base_info, chunks


def _detect_openapi_auth(spec: dict) -> str:
    defs = (
        spec.get("components", {}).get("securitySchemes", {})
        or spec.get("securityDefinitions", {})
    )
    for name, scheme in defs.items():
        t = (scheme.get("type") or "").lower()
        s = (scheme.get("scheme") or "").lower()
        if t == "http" and s == "bearer":
            return "BEARER"
        if t in ("apikey", "api_key"):
            return "API_KEY"
        if t == "http" and s == "basic":
            return "BASIC"
        if t == "oauth2":
            return "BEARER"
    return "NONE"


def _chunk_postman(text: str) -> tuple[dict, list[EndpointChunk]]:
    collection = json.loads(text)
    info = collection.get("info", {})
    base_info = {
        "name":        info.get("name", ""),
        "description": "",
        "base_url":    _extract_postman_base_url(collection),
        "auth_type":   _extract_postman_auth(collection),
    }
    chunks: list[EndpointChunk] = []
    _collect_postman_items(collection.get("item", []), base_info, chunks)
    return base_info, chunks


def _collect_postman_items(items: list, base_info: dict, chunks: list):
    for item in items:
        if "item" in item:
            _collect_postman_items(item["item"], base_info, chunks)
        elif "request" in item:
            req = item["request"]
            method = (req.get("method") or "GET").upper()
            url = req.get("url", {})
            if isinstance(url, str):
                path = "/" + "/".join(url.split("/")[3:]) if "/" in url else url
            else:
                path = "/" + "/".join(url.get("path", []))
            chunks.append(EndpointChunk(
                method=method,
                path=path,
                hint=f"{method} {path}",
                content=json.dumps(item, indent=2),
                base_info=base_info,
            ))


def _extract_postman_base_url(collection: dict) -> str:
    items = collection.get("item", [])
    for item in items:
        req = item.get("request", {})
        url = req.get("url", {})
        if isinstance(url, dict) and url.get("host"):
            scheme = url.get("protocol", "https")
            host = ".".join(url["host"]) if isinstance(url["host"], list) else url["host"]
            return f"{scheme}://{host}"
        if isinstance(url, str) and url.startswith("http"):
            parts = url.split("/")
            return "/".join(parts[:3])
    return ""


def _extract_postman_auth(collection: dict) -> str:
    auth = collection.get("auth", {})
    atype = (auth.get("type") or "").lower()
    if atype == "bearer":
        return "BEARER"
    if atype in ("apikey", "api_key"):
        return "API_KEY"
    if atype == "basic":
        return "BASIC"
    return "NONE"


# ── Option C: Unstructured two-pass ──────────────────────────────────────────

_INDEX_SYSTEM = """You are an API documentation analyst.
Read the provided text and list EVERY API endpoint mentioned.
Return ONLY a JSON array — no other text.
Each element: {"method": "GET", "path": "/resource/{id}"}
If no endpoints found, return [].
"""

_ENDPOINT_SYSTEM = """You are an API documentation analyst.
Extract the COMPLETE definition of the ONE specific endpoint indicated.
Return a single JSON object with this shape:
{
  "path": "/resource/{id}",
  "method": "GET",
  "name": "snake_case_name",
  "description": "what this endpoint does",
  "parameters": [
    {"name": "id", "type": "string", "required": true, "location": "path", "description": "..."}
  ],
  "response_example": {}
}
Only extract the endpoint indicated — ignore all others in the text.
"""

_BASE_INFO_SYSTEM = """Extract the API-level metadata from the documentation.
Return a JSON object:
{"name": "...", "description": "...", "base_url": "https://...", "auth_type": "BEARER|API_KEY|BASIC|NONE"}
"""


async def _chunk_unstructured(text: str) -> tuple[dict, list[EndpointChunk]]:
    # Pass 1: extract endpoint index + base info in parallel
    index_task     = chat_json(_INDEX_SYSTEM, text[:60_000])
    base_info_task = chat_json(_BASE_INFO_SYSTEM, text[:8_000])
    index_raw, base_info = await asyncio.gather(index_task, base_info_task)

    # Ensure base_info is a dict regardless of what the LLM returned
    if not isinstance(base_info, dict):
        base_info = {}

    # index_raw could be:
    #   - a list directly  [{"method":"GET","path":"/foo"}, ...]
    #   - a dict with an "endpoints" key  {"endpoints": [...]}
    #   - a dict where some other key holds the list
    #   - anything else (string, int, …) → treat as empty
    if isinstance(index_raw, list):
        endpoints = index_raw
    elif isinstance(index_raw, dict):
        val = index_raw.get("endpoints")
        if not isinstance(val, list):
            # Find the first value that is actually a list
            val = next((v for v in index_raw.values() if isinstance(v, list)), [])
        endpoints = val
    else:
        endpoints = []

    # Keep only valid endpoint dicts that carry a path
    endpoints = [ep for ep in endpoints if isinstance(ep, dict) and ep.get("path")]

    if not endpoints:
        return base_info, []

    # Pass 2: targeted extraction per endpoint (parallel)
    tasks = [
        _extract_single(text, ep.get("method", "GET"), ep.get("path", "/"))
        for ep in endpoints
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    chunks: list[EndpointChunk] = []
    for ep, result in zip(endpoints, results):
        if isinstance(result, Exception):
            continue
        method = ep.get("method", "GET").upper()
        path   = ep.get("path", "/")
        chunks.append(EndpointChunk(
            method=method,
            path=path,
            hint=f"{method} {path}",
            content=json.dumps(result, indent=2),
            base_info=base_info,
        ))
    return base_info, chunks


async def _extract_single(text: str, method: str, path: str) -> dict:
    section = _find_section(text, method, path)
    prompt  = f"Extract: {method.upper()} {path}\n\nDocumentation:\n{section}"
    return await chat_json(_ENDPOINT_SYSTEM, prompt, max_tokens=2048)


# Boundaries: markdown headings (##/###/####) or bare HTTP-method lines
_BOUNDARY = re.compile(
    r'^(?:#{2,4}\s+.+|(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/\S*)',
    re.MULTILINE | re.IGNORECASE,
)


def _find_section(text: str, method: str, path: str) -> str:
    """
    Find the semantic section for an endpoint.
    Uses heading/HTTP-method boundary lines instead of a fixed char window,
    so each returned section maps cleanly to one endpoint with no overlap.
    """
    # Locate the endpoint reference in the text
    pattern = re.compile(
        rf'\b{re.escape(method.upper())}\b.{{0,80}}{re.escape(path)}',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        pattern = re.compile(re.escape(path), re.IGNORECASE)
        match   = pattern.search(text)

    if not match:
        return text[:4_000]

    match_pos = match.start()

    # Walk boundary positions to find the enclosing section
    boundaries = [m.start() for m in _BOUNDARY.finditer(text)]

    section_start = 0
    section_end   = len(text)
    for pos in boundaries:
        if pos <= match_pos:
            section_start = pos
        elif section_end == len(text):
            section_end = pos

    section = text[section_start:section_end]

    # Cap very long sections to avoid overwhelming the LLM
    if len(section) > 4_000:
        context_start = max(section_start, match_pos - 300)
        section = text[context_start: min(section_end, context_start + 4_000)]

    return section
