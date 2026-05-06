import re
from models.api_definition import ApiDefinition, ApiEndpoint


def _tool_name(api_id: str, ep_id: str) -> str:
    """Stable, unique OpenAI-safe function name (a-z0-9_, max 64)."""
    return f"t_{api_id[:8]}_{ep_id[:8]}"


def _friendly_tool_name(api: ApiDefinition, ep: ApiEndpoint) -> str:
    """
    Prefer a human-readable endpoint name/operationId when available so the UI
    mirrors the uploaded spec. Fall back to a stable synthetic name if needed.
    """
    candidate = (ep.name or "").strip()
    if not candidate:
        candidate = f"{ep.method.lower()}_{ep.path.strip('/').replace('/', '_').replace('{', '').replace('}', '').replace('-', '_')}"
    candidate = re.sub(r"[^a-zA-Z0-9_]", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_").lower()
    if not candidate:
        return _tool_name(api.id, ep.id)
    if len(candidate) > 48:
        candidate = candidate[:48].rstrip("_")
    return candidate


def _sanitize_schema(schema: object) -> dict:
    """
    Recursively fix a JSON schema so OpenAI accepts it as a function parameter schema.

    Rules enforced:
    - array type must have 'items'  (OpenAI rejects arrays without it)
    - object type gets 'properties' if missing
    - $ref entries are replaced with a plain string schema (can't be resolved here)
    """
    if not isinstance(schema, dict):
        return {"type": "string"}

    schema = dict(schema)

    # Replace unresolvable $ref with a plain string fallback
    if "$ref" in schema:
        return {"type": "string", "description": f"(ref: {schema['$ref']})"}

    t = schema.get("type")

    if t == "array":
        if "items" not in schema:
            schema["items"] = {"type": "string"}
        else:
            schema["items"] = _sanitize_schema(schema["items"])

    elif t == "object" or "properties" in schema:
        if "properties" not in schema:
            schema["properties"] = {}
        schema["properties"] = {
            k: _sanitize_schema(v) for k, v in schema["properties"].items()
        }

    # Recurse into composition keywords
    for key in ("allOf", "anyOf", "oneOf"):
        if key in schema and isinstance(schema[key], list):
            schema[key] = [_sanitize_schema(s) for s in schema[key]]

    return schema


def endpoint_to_tool(api: ApiDefinition, ep: ApiEndpoint) -> dict:
    desc = f"{api.name}: {ep.description or ep.name or f'{ep.method} {ep.path}'}"
    if len(desc) > 200:
        desc = desc[:197] + "..."

    raw = ep.input_schema if isinstance(ep.input_schema, dict) else {}
    params = _sanitize_schema(raw)
    if params.get("type") != "object":
        params = {"type": "object", "properties": {}}

    return {
        "type": "function",
        "function": {
            "name": _friendly_tool_name(api, ep),
            "description": desc,
            "parameters": params,
        },
    }


def api_to_tools(api: ApiDefinition) -> list[dict]:
    return [endpoint_to_tool(api, ep) for ep in (api.endpoints or [])]


def resolve_tool_call(tool_name: str, db) -> tuple:
    """Return (ApiDefinition | None, ApiEndpoint | None) for a tool function name."""
    # Match by computing the friendly name for every endpoint (handles sanitized names
    # like "get_github_user" vs stored names like "Get GitHub User").
    for ep in db.query(ApiEndpoint).all():
        api = ep.definition
        if api and _friendly_tool_name(api, ep) == tool_name:
            return api, ep

    # Legacy fallback: t_<api_prefix>_<ep_prefix> synthetic names
    parts = tool_name.split("_")
    if len(parts) == 3 and parts[0] == "t":
        api_prefix, ep_prefix = parts[1], parts[2]
        ep = db.query(ApiEndpoint).filter(ApiEndpoint.id.like(f"{ep_prefix}%")).first()
        if ep:
            api = db.query(ApiDefinition).filter(ApiDefinition.id.like(f"{api_prefix}%")).first()
            return api, ep

    return None, None
