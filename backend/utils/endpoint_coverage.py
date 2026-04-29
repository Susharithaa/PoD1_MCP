"""
Endpoint coverage validator.

Compares the reference endpoints (extracted from the source file by ParsingAgent)
with the generated endpoints (produced by SchemaAgent + ReconciliationAgent).

Produces a CoverageReport that answers:
  - Which reference endpoints were successfully generated?
  - Which reference endpoints are missing from the output?
  - Which generated endpoints have no matching reference (potential hallucination)?
  - What is the overall coverage percentage?
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class EndpointMatch:
    method: str
    path: str
    status: str   # "matched" | "missing" | "extra"
    generated_name: str = ""


@dataclass
class CoverageReport:
    total_reference: int
    total_generated: int
    matched: int
    missing: int
    extra: int
    coverage_pct: float          # matched / total_reference * 100
    matched_endpoints: list = field(default_factory=list)
    missing_endpoints: list = field(default_factory=list)
    extra_endpoints: list = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.missing == 0

    def summary(self) -> str:
        return (
            f"{self.matched}/{self.total_reference} reference endpoints covered "
            f"({self.coverage_pct:.0f}%)"
            + (f" | {self.missing} missing" if self.missing else "")
            + (f" | {self.extra} extra" if self.extra else "")
        )


# ── Public API ────────────────────────────────────────────────────────────────

def compare(reference_chunks: list, generated_endpoints: list) -> CoverageReport:
    """
    reference_chunks: list of chunk dicts from session.extracted_schema._chunks
                      each has: method, path
    generated_endpoints: list of endpoint dicts from session.draft_api.endpoints
                         each has: method, path, name (optional)
    """
    ref_keys   = {_normalise(c["method"], c["path"]): c for c in reference_chunks}
    gen_map    = {_normalise(e["method"], e["path"]): e for e in generated_endpoints}

    matched_list  = []
    missing_list  = []
    extra_list    = []

    for key, ref in ref_keys.items():
        gen = gen_map.get(key)
        if gen:
            matched_list.append(EndpointMatch(
                method=ref["method"],
                path=ref["path"],
                status="matched",
                generated_name=gen.get("name", ""),
            ))
        else:
            # Try relaxed path-structure match (param names may differ: {id} vs {userId})
            relaxed_gen = _find_relaxed(key, gen_map)
            if relaxed_gen:
                matched_list.append(EndpointMatch(
                    method=ref["method"],
                    path=ref["path"],
                    status="matched",
                    generated_name=relaxed_gen.get("name", ""),
                ))
            else:
                missing_list.append(EndpointMatch(
                    method=ref["method"],
                    path=ref["path"],
                    status="missing",
                ))

    for key, gen in gen_map.items():
        if key not in ref_keys and not _find_relaxed(key, ref_keys):
            extra_list.append(EndpointMatch(
                method=gen["method"],
                path=gen["path"],
                status="extra",
                generated_name=gen.get("name", ""),
            ))

    total_ref = len(ref_keys)
    matched   = len(matched_list)
    coverage  = (matched / total_ref * 100) if total_ref else 0.0

    return CoverageReport(
        total_reference=total_ref,
        total_generated=len(gen_map),
        matched=matched,
        missing=len(missing_list),
        extra=len(extra_list),
        coverage_pct=coverage,
        matched_endpoints=[_ep_dict(e) for e in matched_list],
        missing_endpoints=[_ep_dict(e) for e in missing_list],
        extra_endpoints=[_ep_dict(e) for e in extra_list],
    )


def compare_from_session(session) -> CoverageReport:
    """Convenience wrapper that reads directly from an AgentSession."""
    chunks     = (session.extracted_schema or {}).get("_chunks", [])
    endpoints  = (session.draft_api or {}).get("endpoints", [])
    return compare(chunks, endpoints)


# ── Normalisation helpers ─────────────────────────────────────────────────────

def _normalise(method: str, path: str) -> str:
    """Canonical key: uppercase method + lowercase path with trailing slash stripped."""
    m = (method or "GET").upper().strip()
    p = (path or "/").lower().rstrip("/") or "/"
    return f"{m}:{p}"


def _path_structure(path: str) -> str:
    """Replace all {param} tokens with {} for structural comparison."""
    return re.sub(r"\{[^}]+\}", "{}", path.lower().rstrip("/") or "/")


def _find_relaxed(key: str, candidate_map: dict):
    """
    Look for a match where method is identical but path structure matches
    (param names may differ: {id} vs {userId}).
    Returns the matched candidate dict or None.
    """
    method, path = key.split(":", 1)
    struct = _path_structure(path)
    for ckey, cval in candidate_map.items():
        cmethod, cpath = ckey.split(":", 1)
        if cmethod == method and _path_structure(cpath) == struct:
            return cval
    return None


def _ep_dict(ep: EndpointMatch) -> dict:
    d = {"method": ep.method, "path": ep.path, "status": ep.status}
    if ep.generated_name:
        d["name"] = ep.generated_name
    return d
