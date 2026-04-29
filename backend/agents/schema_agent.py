"""
SchemaAgent — converts per-endpoint chunks into clean OpenAPI-compatible definitions.

Architecture:
  1. Deterministic extractor  → GroundTruth (method, path, params — no LLM)
  2. LLM enrichment           → name, description, response schema, body descriptions
  3. Endpoint validator       → auto-fix hallucinations, anchor method/path/params
"""

import asyncio
import json
import re as _re
from agents.base import BaseAgent
from models.agent_session import AgentSession
from llm.client import chat_json
from utils.deterministic_extractor import extract as det_extract
from utils.endpoint_validator import validate_and_fix
from utils.endpoint_coverage import compare

_META_SYSTEM = """You are an API schema designer.
Given API metadata, return a clean JSON object:
{
  "name": "Human-readable API name",
  "description": "What this API does in 1-2 sentences",
  "base_url": "https://api.example.com",
  "version": "1.0.0",
  "auth_type": "BEARER | API_KEY | BASIC | NONE"
}
Return ONLY the JSON object."""

_ENDPOINT_SYSTEM = """You are an API schema enricher.

The METHOD, PATH, and PARAMETERS listed in ANCHOR VALUES below were extracted
deterministically — do NOT change them. Your job is ONLY to:
1. Write a descriptive snake_case function name
2. Write a clear one-sentence description
3. Add helpful descriptions to each parameter
4. Infer the request body schema from examples in the raw data (POST/PUT/PATCH only)
5. Infer the output/response schema structure

Return a single JSON object:
{
  "name": "snake_case_function_name",
  "description": "what this endpoint does",
  "path": "<must match ANCHOR>",
  "method": "<must match ANCHOR>",
  "auth_type": "BEARER | API_KEY | BASIC | NONE",
  "input_schema": {
    "type": "object",
    "properties": {
      "param": {"type": "string", "description": "what this param does"}
    },
    "required": ["param"]
  },
  "output_schema": {"type": "object", "properties": {}},
  "headers": []
}

RULES:
- method and path MUST match the ANCHOR VALUES exactly — never alter them
- input_schema must include ALL anchored parameters with their correct types
- required[] must list every path param and every truly required param
- Types must be: string | integer | number | boolean | array | object
- Extract request body schema from any request examples found in the raw data
Return ONLY the JSON object."""


_MAX_CONCURRENT = 8

# Formats whose chunks are fully structured — no LLM needed to extract schema
_STRUCTURED_FORMATS = {"openapi_json", "postman"}


def _build_from_structured(chunk: dict, ground_truth) -> dict:
    """Build an endpoint dict from structured chunk content without any LLM call."""
    operation: dict = {}
    try:
        data = json.loads(chunk.get("content") or "{}")
        for path_item in data.values():
            if isinstance(path_item, dict):
                for op in path_item.values():
                    if isinstance(op, dict):
                        operation = op
                        break
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    raw_name = operation.get("operationId") or (
        chunk.get("hint", "")
        .replace(" ", "_").replace("/", "_")
        .replace("{", "").replace("}", "").strip("_")
    )
    # camelCase / PascalCase → snake_case, strip non-identifier chars
    name = _re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", raw_name)
    name = _re.sub(r"[^a-z0-9_]", "_", name.lower())
    name = _re.sub(r"_+", "_", name).strip("_") or "endpoint"

    description = (
        operation.get("description")
        or operation.get("summary")
        or f"{ground_truth.method} {ground_truth.path}"
    )

    # Build input_schema from deterministic params + body
    properties: dict = {}
    required: list = []

    for p in ground_truth.path_params + ground_truth.query_params:
        properties[p["name"]] = {
            "type": p.get("type", "string"),
            "description": p.get("description", ""),
        }
        if p.get("required"):
            required.append(p["name"])

    if ground_truth.body_schema and isinstance(ground_truth.body_schema, dict):
        for k, v in (ground_truth.body_schema.get("properties") or {}).items():
            properties[k] = v
        for k in (ground_truth.body_schema.get("required") or []):
            if k not in required:
                required.append(k)

    input_schema: dict = {"type": "object", "properties": properties}
    if required:
        input_schema["required"] = required

    auth_type = "NONE"
    for h in ground_truth.headers:
        if h.get("name", "").lower() == "authorization":
            auth_type = "BEARER"
            break

    return {
        "name":          name,
        "description":   description,
        "method":        ground_truth.method,
        "path":          ground_truth.path,
        "auth_type":     auth_type,
        "input_schema":  input_schema,
        "output_schema": {"type": "object", "properties": {}},
        "headers":       ground_truth.headers,
    }


class SchemaAgent(BaseAgent):
    name = "schema_agent"

    async def run(self, session: AgentSession) -> AgentSession:
        extracted = session.extracted_schema or {}
        chunks    = extracted.get("_chunks", [])
        fmt       = extracted.get("_fmt", "")

        if not chunks:
            raise ValueError("No endpoint chunks found — ParsingAgent may have failed.")

        sem = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _throttled(c):
            async with sem:
                return await self._build_endpoint(c, fmt)

        meta_task      = self._build_meta(extracted)
        endpoint_tasks = [_throttled(c) for c in chunks]

        meta, *results = await asyncio.gather(meta_task, *endpoint_tasks)

        # Unpack (endpoint, report) tuples; filter None results
        valid_endpoints: list = []
        validation_reports: list = []
        for item in results:
            if item is None:
                continue
            ep, report = item
            if ep and ep.get("path"):
                valid_endpoints.append(ep)
                validation_reports.append({
                    "hint":          report.hint,
                    "is_valid":      report.is_valid,
                    "was_auto_fixed": report.was_auto_fixed,
                    "issues":        report.issues,
                })

        session.draft_api = {
            "name":        meta.get("name") or extracted.get("name", ""),
            "description": meta.get("description", ""),
            "base_url":    meta.get("base_url") or extracted.get("base_url", ""),
            "version":     meta.get("version", "1.0.0"),
            "auth_type":   meta.get("auth_type") or extracted.get("auth_type", "NONE"),
            "endpoints":   valid_endpoints,
        }
        session.validation_reports = validation_reports

        # Coverage: compare reference chunks (from file) vs generated endpoints
        coverage = compare(chunks, valid_endpoints)
        session.coverage_report = {
            "total_reference": coverage.total_reference,
            "total_generated": coverage.total_generated,
            "matched":         coverage.matched,
            "missing":         coverage.missing,
            "extra":           coverage.extra,
            "coverage_pct":    round(coverage.coverage_pct, 1),
            "missing_endpoints": coverage.missing_endpoints,
            "extra_endpoints":   coverage.extra_endpoints,
        }
        return session

    async def _build_meta(self, extracted: dict) -> dict:
        prompt = json.dumps({
            "name":      extracted.get("name", ""),
            "base_url":  extracted.get("base_url", ""),
            "auth_type": extracted.get("auth_type", ""),
        })
        try:
            return await chat_json(_META_SYSTEM, prompt, max_tokens=512)
        except Exception:
            return {}

    async def _build_endpoint(self, chunk: dict, fmt: str) -> tuple | None:
        ground_truth = det_extract(chunk)

        # Structured formats (OpenAPI JSON, Postman): all data is already in the chunk.
        # Skip LLM entirely — guaranteed extraction for every endpoint.
        if fmt in _STRUCTURED_FORMATS:
            result = _build_from_structured(chunk, ground_truth)
            fixed_ep, report = validate_and_fix(result, ground_truth)
            return fixed_ep, report

        # Unstructured: LLM enrichment with deterministic fallback on failure
        anchor_section = json.dumps({
            "method":       ground_truth.method,
            "path":         ground_truth.path,
            "path_params":  ground_truth.path_params,
            "query_params": ground_truth.query_params,
        }, indent=2)

        prompt = (
            f"ANCHOR VALUES (do not change):\n{anchor_section}\n\n"
            f"Endpoint: {chunk['hint']}\n\nRaw data:\n{chunk['content']}"
        )

        try:
            result = await chat_json(_ENDPOINT_SYSTEM, prompt, max_tokens=2048)
            result["method"] = ground_truth.method
            result["path"]   = ground_truth.path
        except Exception:
            # Fallback to structured extraction rather than silently dropping the endpoint
            result = _build_from_structured(chunk, ground_truth)

        fixed_ep, report = validate_and_fix(result, ground_truth)
        return fixed_ep, report
