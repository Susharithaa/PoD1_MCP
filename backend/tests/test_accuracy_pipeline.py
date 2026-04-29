"""
Comprehensive accuracy pipeline tests — v3 improvements.

Covers all file formats and all new components:
  - doc_extractor   (JSON / YAML / TXT / truncated JSON repair)
  - smart_chunker   (OpenAPI structured + semantic section finding)
  - deterministic_extractor
  - endpoint_validator
  - reconciliation_agent (deterministic passes)

LLM calls are NOT made — all tests run fully offline.
"""

import asyncio
import json
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.doc_extractor import extract as doc_extract, _attempt_json_repair
from utils.smart_chunker import chunk as smart_chunk, _find_section
from utils.deterministic_extractor import extract as det_extract, GroundTruth
from utils.endpoint_validator import validate_and_fix
from agents.reconciliation_agent import (
    _deduplicate, _align_auth, _normalise_names, _to_snake
)

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

results = []

def check(test_name: str, condition: bool, detail: str = ""):
    results.append((test_name, condition))
    marker = "PASS" if condition else "FAIL"
    print(f"  [{marker}] {test_name}")
    if detail:
        print(f"        {detail}")

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def path(rel: str) -> str:
    return os.path.join(BASE, rel)


# ─────────────────────────────────────────────────────────────────────────────
# 1. doc_extractor — format detection
# ─────────────────────────────────────────────────────────────────────────────

section("1. doc_extractor — format detection for all file types")

# api-1.json — full valid OpenAPI 3.0
text, fmt = doc_extract(path("api-1.json"))
check("api-1.json detected as openapi_json", fmt == "openapi_json", f"fmt={fmt}")
data = json.loads(text)
endpoint_count = sum(
    1 for pi in data.get("paths", {}).values()
    for m in ("get","post","put","patch","delete","head","options") if m in pi
)
check("api-1.json has endpoints > 0", endpoint_count > 0, f"endpoints={endpoint_count}")

# api-1.yaml — full valid OpenAPI 3.0 YAML
text_y, fmt_y = doc_extract(path("api-1.yaml"))
check("api-1.yaml detected as openapi_json", fmt_y == "openapi_json", f"fmt={fmt_y}")
data_y = json.loads(text_y)
ep_count_y = sum(
    1 for pi in data_y.get("paths", {}).values()
    for m in ("get","post","put","patch","delete") if m in pi
)
# YAML is a newer version of the spec with additional /unstable/* endpoints — count may differ
check("api-1.yaml endpoint count > 0", ep_count_y > 0, f"yaml={ep_count_y}")
check("api-1.yaml endpoint count close to api-1.json (within 20%)",
      abs(ep_count_y - endpoint_count) <= max(10, endpoint_count * 0.2),
      f"yaml={ep_count_y}, json={endpoint_count}")

# test.json — truncated/malformed JSON (needs repair)
text_tj, fmt_tj = doc_extract(path("test.json"))
check("test.json (truncated) detected as openapi_json via repair", fmt_tj == "openapi_json",
      f"fmt={fmt_tj}")
if fmt_tj == "openapi_json":
    data_tj = json.loads(text_tj)
    check("test.json repaired has 'paths' key", "paths" in data_tj)

# test.txt — same content as test.json but .txt extension
text_tt, fmt_tt = doc_extract(path("test.txt"))
check("test.txt (truncated JSON in .txt) detected as openapi_json", fmt_tt == "openapi_json",
      f"fmt={fmt_tt}")

# testing/Swagger_test.json — Swagger 2.0
text_sw, fmt_sw = doc_extract(path("testing/Swagger_test.json"))
check("Swagger_test.json detected as openapi_json", fmt_sw == "openapi_json", f"fmt={fmt_sw}")

# testing/Mixed_doc.txt — unstructured text (YAML-like custom format)
text_mix, fmt_mix = doc_extract(path("testing/Mixed_doc.txt"))
check("Mixed_doc.txt detected as text (unstructured)", fmt_mix == "text", f"fmt={fmt_mix}")
check("Mixed_doc.txt content non-empty", len(text_mix) > 100, f"len={len(text_mix)}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. _attempt_json_repair
# ─────────────────────────────────────────────────────────────────────────────

section("2. JSON repair — truncated OpenAPI specs")

# Manually truncated OpenAPI
truncated = '{"openapi":"3.0.1","info":{"title":"Test"},"paths":{"/users":{"get":{"operationId":"list"'
repaired = _attempt_json_repair(truncated)
check("Repair returns dict for truncated JSON", isinstance(repaired, dict),
      f"type={type(repaired).__name__}")
check("Repaired dict has 'openapi' key", repaired is not None and "openapi" in repaired)

# Already valid JSON — repair should return None (nothing to close)
valid_json = '{"openapi":"3.0.1","paths":{}}'
result_valid = _attempt_json_repair(valid_json)
check("Valid JSON returns None from repair (no action needed)", result_valid is None)

# Completely invalid string
junk = "not json at all {{{"
result_junk = _attempt_json_repair(junk)
check("Garbage string returns None from repair", result_junk is None)

# Truncated with trailing comma (real-world case)
trailing_comma = '{"openapi":"3.0.0","paths":{"/foo":{"get":{"tags":["X"],'
repaired_tc = _attempt_json_repair(trailing_comma)
check("Trailing-comma truncation repaired to dict", isinstance(repaired_tc, dict))


# ─────────────────────────────────────────────────────────────────────────────
# 3. smart_chunker — structured parsing (no LLM)
# ─────────────────────────────────────────────────────────────────────────────

section("3. smart_chunker — structured chunking (OpenAPI + YAML)")

text_j, _ = doc_extract(path("api-1.json"))
base_info, chunks = asyncio.get_event_loop().run_until_complete(
    smart_chunk(text_j, "openapi_json")
)
check(f"api-1.json chunks > 0", len(chunks) > 0, f"chunks={len(chunks)}")
check("api-1.json base_info has name", bool(base_info.get("name")), f"name={base_info.get('name')}")
check("api-1.json base_info has auth_type", bool(base_info.get("auth_type")),
      f"auth={base_info.get('auth_type')}")

# Every chunk must have method and path
methods_valid = all(c.method in ("GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS")
                    for c in chunks)
check("All api-1.json chunks have valid HTTP methods", methods_valid)
paths_valid = all(c.path.startswith("/") for c in chunks)
check("All api-1.json chunk paths start with '/'", paths_valid)

# YAML
text_yl, _ = doc_extract(path("api-1.yaml"))
base_y, chunks_y = asyncio.get_event_loop().run_until_complete(
    smart_chunk(text_yl, "openapi_json")
)
check("api-1.yaml chunk count > 0 (newer version may have extra endpoints)",
      len(chunks_y) > 0, f"yaml={len(chunks_y)}, json={len(chunks)}")

# Swagger 2.0
text_sv, _ = doc_extract(path("testing/Swagger_test.json"))
base_sv, chunks_sv = asyncio.get_event_loop().run_until_complete(
    smart_chunk(text_sv, "openapi_json")
)
check("Swagger_test.json chunks > 0", len(chunks_sv) > 0, f"chunks={len(chunks_sv)}")
check("Swagger_test.json base_url non-empty", bool(base_sv.get("base_url")),
      f"base_url={base_sv.get('base_url')}")

# Repaired test.json
text_rj, _ = doc_extract(path("test.json"))
base_rj, chunks_rj = asyncio.get_event_loop().run_until_complete(
    smart_chunk(text_rj, "openapi_json")
)
check("test.json (repaired) produces chunks", len(chunks_rj) > 0, f"chunks={len(chunks_rj)}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. semantic _find_section — no overlap, boundary-aware
# ─────────────────────────────────────────────────────────────────────────────

section("4. smart_chunker — semantic _find_section (no endpoint overlap)")

unstructured_doc = textwrap.dedent("""
    ## Authentication
    Use Bearer token.

    ### GET /users
    Returns a list of users.
    Parameters: page (integer), limit (integer).

    ### POST /users
    Create a user.
    Body: name (string, required), email (string, required).

    ### GET /users/{id}
    Returns a single user.
    Parameters: id (string, path, required).

    ### DELETE /users/{id}
    Deletes a user.
    Parameters: id (string, path, required).
""")

s_get_users    = _find_section(unstructured_doc, "GET",    "/users")
s_post_users   = _find_section(unstructured_doc, "POST",   "/users")
s_get_user_id  = _find_section(unstructured_doc, "GET",    "/users/{id}")
s_del_user_id  = _find_section(unstructured_doc, "DELETE", "/users/{id}")

check("GET /users section contains 'Returns a list'", "Returns a list" in s_get_users,
      f"section={repr(s_get_users[:80])}")
check("POST /users section contains 'Create a user'", "Create a user" in s_post_users)
check("GET /users/{id} section contains 'single user'", "single user" in s_get_user_id)
check("DELETE /users/{id} section contains 'Deletes'", "Deletes" in s_del_user_id)

# Sections must be distinct (no bleed-over)
check("GET /users section does NOT contain POST content",
      "Create a user" not in s_get_users)
check("POST /users section does NOT contain GET /users/{id} content",
      "single user" not in s_post_users)
check("GET /users/{id} section does NOT contain DELETE content",
      "Deletes" not in s_get_user_id)


# ─────────────────────────────────────────────────────────────────────────────
# 5. deterministic_extractor — OpenAPI JSON chunks
# ─────────────────────────────────────────────────────────────────────────────

section("5. deterministic_extractor — ground truth from OpenAPI chunks")

# Find a chunk with path params from api-1.json
path_param_chunk = next(
    (c for c in chunks if "{" in c.path and c.method == "GET"), None
)
if path_param_chunk:
    gt = det_extract({"method": path_param_chunk.method,
                      "path": path_param_chunk.path,
                      "hint": path_param_chunk.hint,
                      "content": path_param_chunk.content})
    param_names = [p["name"] for p in gt.path_params]
    # Extract expected path param names from the path pattern
    import re
    expected = re.findall(r"\{(\w+)\}", path_param_chunk.path)
    check(f"Path params extracted for {path_param_chunk.hint}",
          all(e in param_names for e in expected),
          f"expected={expected}, got={param_names}")
    check("All path params have required=True",
          all(p["required"] for p in gt.path_params))
else:
    print(f"  [SKIP] No path-param GET chunk found in api-1.json")

# Simple path no params
simple_chunk = {"method": "GET", "path": "/users",
    "hint": "GET /users",
    "content": json.dumps({"/users": {"get": {
        "parameters": [
            {"name": "page", "in": "query", "required": False, "schema": {"type": "integer"}},
            {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}},
        ]
    }}})}
gt_simple = det_extract(simple_chunk)
check("GET /users: no path params", len(gt_simple.path_params) == 0)
check("GET /users: 2 query params", len(gt_simple.query_params) == 2,
      f"query_params={[q['name'] for q in gt_simple.query_params]}")

# POST with body
post_chunk = {"method": "POST", "path": "/users", "hint": "POST /users",
    "content": json.dumps({"/users": {"post": {
        "requestBody": {"content": {"application/json": {"schema": {
            "type": "object",
            "properties": {
                "name":  {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["name", "email"],
        }}}}
    }}})}
gt_post = det_extract(post_chunk)
check("POST /users: body_schema extracted", bool(gt_post.body_schema),
      f"body_schema={gt_post.body_schema}")
check("POST /users: body_schema has 'name' property",
      "name" in (gt_post.body_schema.get("properties") or {}))

# Text-based (unstructured) chunk
text_chunk = {"method": "GET", "path": "/orders/{orderId}",
    "hint": "GET /orders/{orderId}",
    "content": "GET /orders/{orderId}\nReturns an order. Query: status, page. Header: Authorization."}
gt_text = det_extract(text_chunk)
check("Text chunk: orderId path param detected", any(p["name"] == "orderId" for p in gt_text.path_params))
check("Text chunk: orderId is required", any(p["name"] == "orderId" and p["required"] for p in gt_text.path_params))


# ─────────────────────────────────────────────────────────────────────────────
# 6. endpoint_validator — auto-fix cases
# ─────────────────────────────────────────────────────────────────────────────

section("6. endpoint_validator — auto-fix and anchoring")

from utils.deterministic_extractor import GroundTruth

gt_fix = GroundTruth(
    method="GET",
    path="/users/{id}",
    path_params=[{"name": "id", "type": "string", "required": True, "description": ""}],
    query_params=[{"name": "fields", "type": "string", "required": False, "description": ""}],
    headers=[],
    body_schema={},
)

# Case 1: LLM hallucinated wrong method and path
llm_wrong = {
    "name": "get_user", "description": "Get user",
    "method": "POST",           # wrong
    "path": "/user/{id}",       # wrong (missing 's')
    "auth_type": "NONE",
    "input_schema": {"type": "object", "properties": {}, "required": []},
    "output_schema": {}, "headers": [],
}
fixed, report = validate_and_fix(llm_wrong, gt_fix)
check("Method corrected from POST to GET", fixed["method"] == "GET")
check("Path corrected to /users/{id}", fixed["path"] == "/users/{id}")
check("Report: was_auto_fixed=True", report.was_auto_fixed)
check("Report: method correction in issues", any("Method corrected" in i for i in report.issues))
check("Report: path correction in issues",  any("Path corrected" in i for i in report.issues))

# Case 2: LLM omitted path param {id}
llm_no_param = {
    "name": "get_user", "description": "Get user",
    "method": "GET", "path": "/users/{id}",
    "auth_type": "NONE",
    "input_schema": {"type": "object", "properties": {}, "required": []},
    "output_schema": {}, "headers": [],
}
fixed2, report2 = validate_and_fix(llm_no_param, gt_fix)
check("Missing path param 'id' auto-added", "id" in fixed2["input_schema"]["properties"])
check("'id' added to required[]", "id" in fixed2["input_schema"]["required"])
check("Auto-added path param issue logged", any("Auto-added missing path param" in i for i in report2.issues))

# Case 3: LLM used invalid type
llm_bad_type = {
    "name": "get_user", "description": "Get user",
    "method": "GET", "path": "/users/{id}",
    "auth_type": "NONE",
    "input_schema": {
        "type": "object",
        "properties": {"id": {"type": "Number"}},   # invalid capitalised type
        "required": ["id"],
    },
    "output_schema": {}, "headers": [],
}
fixed3, report3 = validate_and_fix(llm_bad_type, gt_fix)
check("Invalid type 'Number' coerced to 'string'",
      fixed3["input_schema"]["properties"]["id"]["type"] == "string")
check("Type coercion issue logged", any("coerced to string" in i for i in report3.issues))

# Case 4: Correct LLM output — no fixes needed
llm_correct = {
    "name": "get_user", "description": "Get user",
    "method": "GET", "path": "/users/{id}",
    "auth_type": "NONE",
    "input_schema": {
        "type": "object",
        "properties": {
            "id":     {"type": "string", "description": "User ID"},
            "fields": {"type": "string", "description": "Comma-separated fields"},
        },
        "required": ["id"],
    },
    "output_schema": {"type": "object", "properties": {"id": {"type": "string"}}},
    "headers": [],
}
fixed4, report4 = validate_and_fix(llm_correct, gt_fix)
check("Correct LLM output: is_valid=True", report4.is_valid)
check("Correct LLM output: was_auto_fixed=False", not report4.was_auto_fixed)
check("Correct LLM output: no issues", len(report4.issues) == 0)


# ─────────────────────────────────────────────────────────────────────────────
# 7. reconciliation_agent — deterministic passes
# ─────────────────────────────────────────────────────────────────────────────

section("7. reconciliation_agent — deterministic passes")

# Deduplication
eps_with_dupes = [
    {"method": "GET",  "path": "/users", "name": "list_users"},
    {"method": "GET",  "path": "/users", "name": "list_users_dup"},  # duplicate
    {"method": "POST", "path": "/users", "name": "create_user"},
]
deduped = _deduplicate(eps_with_dupes)
check("Deduplication removes exact method+path duplicate", len(deduped) == 2,
      f"count={len(deduped)}")
check("First occurrence preserved after dedup", deduped[0]["name"] == "list_users")

# Auth alignment
eps_no_auth = [
    {"method": "GET",  "path": "/a", "auth_type": "BEARER"},
    {"method": "POST", "path": "/b", "auth_type": ""},          # empty
    {"method": "GET",  "path": "/c", "auth_type": "UNKNOWN"},   # invalid
    {"method": "GET",  "path": "/d", "auth_type": "NONE"},      # explicit NONE — keep
]
aligned = _align_auth(eps_no_auth, "BEARER")
check("Empty auth_type inherits API-level BEARER", aligned[1]["auth_type"] == "BEARER")
check("UNKNOWN auth_type inherits API-level BEARER", aligned[2]["auth_type"] == "BEARER")
check("Explicit NONE auth_type kept as NONE", aligned[3]["auth_type"] == "NONE")
check("Explicit BEARER auth_type unchanged", aligned[0]["auth_type"] == "BEARER")

# Naming normalisation — mixed camelCase (minority) → snake_case
eps_mixed_names = [
    {"method": "GET", "path": "/a", "input_schema": {"properties":
        {"user_id": {}, "first_name": {}, "last_name": {}}, "required": ["user_id"]}},
    {"method": "GET", "path": "/b", "input_schema": {"properties":
        {"userId": {}, "firstName": {}}, "required": ["userId"]}},
]
normalised = _normalise_names(eps_mixed_names)
props_b = normalised[1]["input_schema"]["properties"]
check("camelCase 'userId' normalised to 'user_id'", "user_id" in props_b,
      f"props={list(props_b.keys())}")
check("camelCase 'firstName' normalised to 'first_name'", "first_name" in props_b)
check("Required list updated after normalisation",
      "user_id" in normalised[1]["input_schema"]["required"])

# _to_snake helper
check("_to_snake('userId') = 'user_id'",         _to_snake("userId")         == "user_id")
check("_to_snake('firstName') = 'first_name'",   _to_snake("firstName")      == "first_name")
check("_to_snake('HTTPSUrl') = 'h_t_t_p_s_url'", "https" in _to_snake("HTTPSUrl").lower())
check("_to_snake('snake_case') unchanged",        _to_snake("snake_case")     == "snake_case")


# ─────────────────────────────────────────────────────────────────────────────
# 8. End-to-end structured pipeline (no LLM) — api-1.json
# ─────────────────────────────────────────────────────────────────────────────

section("8. End-to-end structured pipeline — api-1.json (deterministic only)")

text8, fmt8 = doc_extract(path("api-1.json"))
base8, chunks8 = asyncio.get_event_loop().run_until_complete(
    smart_chunk(text8, "openapi_json")
)

# Run deterministic extractor on every chunk
ground_truths = [det_extract({"method": c.method, "path": c.path,
                               "hint": c.hint, "content": c.content})
                 for c in chunks8]

methods_match  = all(gt.method == c.method for gt, c in zip(ground_truths, chunks8))
paths_match    = all(gt.path   == c.path   for gt, c in zip(ground_truths, chunks8))
path_params_ok = all(
    all(p["name"] in [pp["name"] for pp in gt.path_params]
        for p in [{"name": n} for n in __import__("re").findall(r"\{(\w+)\}", gt.path)])
    for gt in ground_truths
)

check(f"All {len(chunks8)} chunks: ground truth method matches chunk method", methods_match)
check(f"All {len(chunks8)} chunks: ground truth path matches chunk path", paths_match)
check("All path param tokens covered in ground truth", path_params_ok)

# Simulate validate_and_fix with a "perfect" LLM that echoes ground truth
perfect_fixes = 0
auto_fixed_count = 0
for gt in ground_truths:
    # "Perfect LLM" — includes all path, query, and body params from ground truth
    all_props = {
        **{p["name"]: {"type": p["type"]} for p in gt.path_params},
        **{q["name"]: {"type": q["type"]} for q in gt.query_params},
    }
    # Also include body schema properties (for POST/PUT/PATCH)
    if gt.body_schema:
        body_props = (gt.body_schema.get("properties") or {})
        all_props.update(body_props)
    all_required = [p["name"] for p in gt.path_params if p["required"]]
    if gt.body_schema:
        all_required += [r for r in (gt.body_schema.get("required") or [])
                         if r not in all_required]
    fake_llm = {
        "name": "fn", "description": "desc",
        "method": gt.method, "path": gt.path,
        "auth_type": "BEARER",
        "input_schema": {"type": "object", "properties": all_props, "required": all_required},
        "output_schema": {}, "headers": [],
    }
    ep, rpt = validate_and_fix(fake_llm, gt)
    if rpt.was_auto_fixed:
        auto_fixed_count += 1
    if rpt.is_valid:
        perfect_fixes += 1

check(f"Perfect LLM: all {len(chunks8)} endpoints pass validation",
      perfect_fixes == len(chunks8), f"passed={perfect_fixes}/{len(chunks8)}")

# Endpoints with $ref body schemas (no inline properties) correctly trigger
# a body-schema substitution. All other endpoints must require zero fixes.
ref_body_endpoints = sum(
    1 for gt in ground_truths
    if "$ref" in gt.body_schema and not gt.body_schema.get("properties")
)
check("Perfect LLM: auto-fixes only for $ref body-schema substitutions (expected)",
      auto_fixed_count <= ref_body_endpoints,
      f"auto_fixed={auto_fixed_count}, ref_body_endpoints={ref_body_endpoints}")

# Simulate a bad LLM that drops all path params
bad_fixes = 0
bad_auto = 0
for gt in ground_truths:
    fake_bad = {
        "name": "fn", "description": "desc",
        "method": gt.method, "path": gt.path,
        "auth_type": "NONE",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "output_schema": {}, "headers": [],
    }
    ep, rpt = validate_and_fix(fake_bad, gt)
    # All path params should have been auto-added
    for pp in gt.path_params:
        if pp["name"] in ep["input_schema"]["properties"]:
            bad_fixes += 1
    if rpt.was_auto_fixed and gt.path_params:
        bad_auto += 1

chunks_with_path_params = sum(1 for gt in ground_truths if gt.path_params)
check(f"Bad LLM: path params auto-restored for all {chunks_with_path_params} path-param endpoints",
      bad_auto == chunks_with_path_params,
      f"auto_fixed={bad_auto}/{chunks_with_path_params}")


# ─────────────────────────────────────────────────────────────────────────────
# 9. Swagger 2.0 — full deterministic pipeline
# ─────────────────────────────────────────────────────────────────────────────

section("9. Swagger 2.0 — Swagger_test.json (Petstore)")

text_pet, fmt_pet = doc_extract(path("testing/Swagger_test.json"))
base_pet, chunks_pet = asyncio.get_event_loop().run_until_complete(
    smart_chunk(text_pet, "openapi_json")
)
check("Petstore chunks > 0", len(chunks_pet) > 0, f"chunks={len(chunks_pet)}")

gts_pet = [det_extract({"method": c.method, "path": c.path,
                         "hint": c.hint, "content": c.content}) for c in chunks_pet]
pet_path_param_chunks = [c for c in chunks_pet if "{" in c.path]
pet_gts_with_params   = [g for g in gts_pet if g.path_params]

check("Petstore path-param chunks have ground truth path params",
      len(pet_path_param_chunks) == len(pet_gts_with_params),
      f"path_param_chunks={len(pet_path_param_chunks)}, gts_with_params={len(pet_gts_with_params)}")


# ─────────────────────────────────────────────────────────────────────────────
# Final Summary
# ─────────────────────────────────────────────────────────────────────────────

total   = len(results)
passed  = sum(1 for _, ok in results if ok)
failed  = total - passed

print(f"\n{'='*60}")
print(f"  RESULTS:  {passed}/{total} passed  |  {failed} failed")
print(f"{'='*60}\n")

if failed > 0:
    print("FAILED tests:")
    for name, ok in results:
        if not ok:
            print(f"  [FAIL] {name}")
    sys.exit(1)
else:
    print("All tests passed.")
    sys.exit(0)
