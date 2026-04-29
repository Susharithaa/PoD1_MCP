"""
Tests for endpoint_coverage.py — validates that reference endpoints (from file)
match generated endpoints and produces accurate coverage reports.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.endpoint_coverage import compare, _normalise, _path_structure
from utils.doc_extractor import extract as doc_extract
from utils.smart_chunker import chunk as smart_chunk

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

results = []

def check(name: str, condition: bool, detail: str = ""):
    results.append((name, condition))
    marker = "PASS" if condition else "FAIL"
    print(f"  [{marker}] {name}")
    if detail:
        print(f"        {detail}")

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def path(rel): return os.path.join(BASE, rel)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Coverage utilities
# ─────────────────────────────────────────────────────────────────────────────

section("1. Normalisation helpers")

check("_normalise uppercases method",    _normalise("get", "/users") == "GET:/users")
check("_normalise strips trailing /",    _normalise("GET", "/users/") == "GET:/users")
check("_normalise lowercases path",      _normalise("POST", "/Users") == "POST:/users")
check("_normalise handles root path",    _normalise("GET", "/") == "GET:/")
check("_path_structure collapses params",
      _path_structure("/users/{id}/posts/{postId}") == "/users/{}/posts/{}")
check("_path_structure keeps static segments",
      _path_structure("/api/v1/users") == "/api/v1/users")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Perfect match — all reference endpoints generated
# ─────────────────────────────────────────────────────────────────────────────

section("2. Perfect coverage — all reference endpoints generated")

ref = [
    {"method": "GET",    "path": "/users"},
    {"method": "POST",   "path": "/users"},
    {"method": "GET",    "path": "/users/{id}"},
    {"method": "DELETE", "path": "/users/{id}"},
]
gen = [
    {"method": "GET",    "path": "/users",      "name": "list_users"},
    {"method": "POST",   "path": "/users",      "name": "create_user"},
    {"method": "GET",    "path": "/users/{id}", "name": "get_user"},
    {"method": "DELETE", "path": "/users/{id}", "name": "delete_user"},
]
report = compare(ref, gen)
check("Perfect: coverage_pct = 100%",    report.coverage_pct == 100.0, f"pct={report.coverage_pct}")
check("Perfect: matched = 4",            report.matched == 4,          f"matched={report.matched}")
check("Perfect: missing = 0",            report.missing == 0,          f"missing={report.missing}")
check("Perfect: extra = 0",              report.extra == 0,            f"extra={report.extra}")
check("Perfect: is_complete = True",     report.is_complete)
check("Perfect: summary text",           "100%" in report.summary(),   f"summary={report.summary()}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Missing endpoints — LLM dropped some
# ─────────────────────────────────────────────────────────────────────────────

section("3. Missing endpoints — LLM dropped some")

gen_partial = [
    {"method": "GET",  "path": "/users",      "name": "list_users"},
    {"method": "POST", "path": "/users",      "name": "create_user"},
    # GET /users/{id} and DELETE /users/{id} missing
]
report_miss = compare(ref, gen_partial)
check("Missing: coverage_pct = 50%",      report_miss.coverage_pct == 50.0, f"pct={report_miss.coverage_pct}")
check("Missing: matched = 2",             report_miss.matched == 2)
check("Missing: missing = 2",             report_miss.missing == 2,         f"missing={report_miss.missing}")
check("Missing: extra = 0",               report_miss.extra == 0)
check("Missing: is_complete = False",     not report_miss.is_complete)
check("Missing: GET /users/{id} in list", any(e["path"] == "/users/{id}" and e["method"] == "GET"
                                              for e in report_miss.missing_endpoints))
check("Missing: DELETE in list",          any(e["method"] == "DELETE"
                                              for e in report_miss.missing_endpoints))


# ─────────────────────────────────────────────────────────────────────────────
# 4. Extra endpoints — LLM hallucinated
# ─────────────────────────────────────────────────────────────────────────────

section("4. Extra endpoints — LLM hallucinated")

gen_extra = gen + [
    {"method": "PATCH", "path": "/users/{id}",         "name": "update_user"},   # not in spec
    {"method": "GET",   "path": "/users/{id}/profile",  "name": "get_profile"},  # not in spec
]
report_extra = compare(ref, gen_extra)
check("Extra: coverage_pct = 100% (all ref matched)", report_extra.coverage_pct == 100.0)
check("Extra: extra = 2",                            report_extra.extra == 2, f"extra={report_extra.extra}")
check("Extra: missing = 0",                          report_extra.missing == 0)
check("Extra: PATCH in extra list",    any(e["method"] == "PATCH" for e in report_extra.extra_endpoints))
check("Extra: /profile in extra list", any("/profile" in e["path"] for e in report_extra.extra_endpoints))


# ─────────────────────────────────────────────────────────────────────────────
# 5. Relaxed path matching — param names differ
# ─────────────────────────────────────────────────────────────────────────────

section("5. Relaxed matching — different param names, same structure")

ref_id = [{"method": "GET", "path": "/users/{id}"}]

# Generated uses {userId} instead of {id} — structural match should succeed
gen_userid = [{"method": "GET", "path": "/users/{userId}", "name": "get_user"}]
report_relaxed = compare(ref_id, gen_userid)
check("Relaxed: {id} vs {userId} counts as matched",
      report_relaxed.matched == 1 and report_relaxed.missing == 0,
      f"matched={report_relaxed.matched}, missing={report_relaxed.missing}")

# Completely different path — should not match
gen_wrong = [{"method": "GET", "path": "/accounts/{id}", "name": "get_account"}]
report_wrong = compare(ref_id, gen_wrong)
check("No relaxed match for different path segments",
      report_wrong.matched == 0 and report_wrong.missing == 1,
      f"matched={report_wrong.matched}, missing={report_wrong.missing}")

# Multi-level path params — both must match structurally
ref_multi = [{"method": "GET", "path": "/orgs/{orgId}/members/{memberId}"}]
gen_multi  = [{"method": "GET", "path": "/orgs/{org}/members/{member}", "name": "get_member"}]
report_multi = compare(ref_multi, gen_multi)
check("Relaxed: multi-level param rename matched",
      report_multi.matched == 1,
      f"matched={report_multi.matched}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Case and slash insensitivity
# ─────────────────────────────────────────────────────────────────────────────

section("6. Method case + trailing slash normalisation")

ref_case = [{"method": "get", "path": "/Users/"},
            {"method": "POST", "path": "/users"}]
gen_case  = [{"method": "GET",  "path": "/users",  "name": "list"},
             {"method": "post", "path": "/users/",  "name": "create"}]
report_case = compare(ref_case, gen_case)
check("Case-insensitive method + trailing slash normalised",
      report_case.matched == 2 and report_case.missing == 0,
      f"matched={report_case.matched}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Empty inputs
# ─────────────────────────────────────────────────────────────────────────────

section("7. Edge cases — empty inputs")

report_empty_ref = compare([], gen)
check("Empty reference: coverage 0 ref, extra = 4",
      report_empty_ref.total_reference == 0 and report_empty_ref.extra == 4)

report_empty_gen = compare(ref, [])
check("Empty generated: 0% coverage, missing = 4",
      report_empty_gen.coverage_pct == 0.0 and report_empty_gen.missing == 4)

report_both_empty = compare([], [])
check("Both empty: 0 everything",
      report_both_empty.total_reference == 0 and report_both_empty.matched == 0)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Real file: api-1.json — simulate perfect + bad generator
# ─────────────────────────────────────────────────────────────────────────────

section("8. Real file api-1.json — coverage simulation")

text, fmt = doc_extract(path("api-1.json"))
base, chunks = asyncio.get_event_loop().run_until_complete(smart_chunk(text, fmt))

ref_chunks = [{"method": c.method, "path": c.path} for c in chunks]

# Perfect generator: returns exactly the reference endpoints
perfect_gen = [{"method": c["method"], "path": c["path"], "name": "fn"} for c in ref_chunks]
r_perfect = compare(ref_chunks, perfect_gen)
check(f"api-1.json perfect generator: 100% coverage ({len(ref_chunks)} endpoints)",
      r_perfect.coverage_pct == 100.0 and r_perfect.missing == 0,
      f"pct={r_perfect.coverage_pct}, matched={r_perfect.matched}")

# Bad generator: drops the last 10 endpoints
bad_gen = perfect_gen[:-10]
r_bad = compare(ref_chunks, bad_gen)
expected_pct = round((len(ref_chunks) - 10) / len(ref_chunks) * 100, 1)
check(f"api-1.json bad generator (drops 10): {expected_pct}% coverage",
      r_bad.missing == 10 and r_bad.matched == len(ref_chunks) - 10,
      f"missing={r_bad.missing}, matched={r_bad.matched}")
check("Missing list has correct count", len(r_bad.missing_endpoints) == 10)

# Hallucinating generator: adds 5 fake endpoints
hallucinated = perfect_gen + [
    {"method": "GET",  "path": "/fake/endpoint1", "name": "fake1"},
    {"method": "POST", "path": "/fake/endpoint2", "name": "fake2"},
    {"method": "GET",  "path": "/fake/endpoint3", "name": "fake3"},
    {"method": "PUT",  "path": "/fake/endpoint4", "name": "fake4"},
    {"method": "DELETE","path": "/fake/endpoint5","name": "fake5"},
]
r_halluc = compare(ref_chunks, hallucinated)
check("api-1.json hallucinating generator: 5 extra detected",
      r_halluc.extra == 5 and r_halluc.coverage_pct == 100.0,
      f"extra={r_halluc.extra}, pct={r_halluc.coverage_pct}")
check("Extra endpoints listed correctly",
      all("/fake/" in e["path"] for e in r_halluc.extra_endpoints))


# ─────────────────────────────────────────────────────────────────────────────
# 9. Swagger Petstore — structured validation
# ─────────────────────────────────────────────────────────────────────────────

section("9. Swagger Petstore — reference vs generated")

sw_text, sw_fmt = doc_extract(path("testing/Swagger_test.json"))
sw_base, sw_chunks = asyncio.get_event_loop().run_until_complete(smart_chunk(sw_text, sw_fmt))
sw_ref = [{"method": c.method, "path": c.path} for c in sw_chunks]

# Perfect Petstore
sw_gen_perfect = [{"method": c["method"], "path": c["path"], "name": "fn"} for c in sw_ref]
r_sw = compare(sw_ref, sw_gen_perfect)
check(f"Petstore perfect: 100% on {len(sw_ref)} endpoints",
      r_sw.coverage_pct == 100.0, f"pct={r_sw.coverage_pct}, matched={r_sw.matched}")

# Petstore: generator uses different param name (e.g. {petId} → {id})
sw_gen_renamed = []
for c in sw_ref:
    import re
    renamed_path = re.sub(r"\{[^}]+\}", "{id}", c["path"])
    sw_gen_renamed.append({"method": c["method"], "path": renamed_path, "name": "fn"})
r_sw_renamed = compare(sw_ref, sw_gen_renamed)
check("Petstore: all endpoints matched even with renamed path params",
      r_sw_renamed.matched == len(sw_ref),
      f"matched={r_sw_renamed.matched}/{len(sw_ref)}")


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

total  = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed

print(f"\n{'='*60}")
print(f"  COVERAGE TESTS:  {passed}/{total} passed  |  {failed} failed")
print(f"{'='*60}\n")

if failed:
    print("FAILED tests:")
    for name, ok in results:
        if not ok:
            print(f"  [FAIL] {name}")
    sys.exit(1)
else:
    print("All coverage tests passed.")
    sys.exit(0)
