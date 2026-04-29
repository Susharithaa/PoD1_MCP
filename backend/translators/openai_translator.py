import re
from models.api_definition import ApiDefinition, ApiEndpoint


def _tool_name(api_id: str, ep_id: str) -> str:
    """Stable, unique OpenAI-safe function name (a-z0-9_, max 64)."""
    return f"t_{api_id[:8]}_{ep_id[:8]}"


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
            "name": _tool_name(api.id, ep.id),
            "description": desc,
            "parameters": params,
        },
    }


def api_to_tools(api: ApiDefinition) -> list[dict]:
    return [endpoint_to_tool(api, ep) for ep in (api.endpoints or [])]


def resolve_tool_call(tool_name: str, db) -> tuple:
    """Return (ApiDefinition | None, ApiEndpoint | None) for a tool function name."""
    parts = tool_name.split("_")
    if len(parts) != 3 or parts[0] != "t":
        return None, None
    api_prefix, ep_prefix = parts[1], parts[2]

    ep = db.query(ApiEndpoint).filter(ApiEndpoint.id.like(f"{ep_prefix}%")).first()
    if not ep:
        return None, None
    api = db.query(ApiDefinition).filter(ApiDefinition.id.like(f"{api_prefix}%")).first()
    return api, ep
