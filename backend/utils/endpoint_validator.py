"""
Pre-HITL endpoint validation and auto-fix.

Uses GroundTruth from deterministic_extractor to anchor the LLM-generated
schema, correct hallucinations, and surface issues for confidence scoring.
"""

from __future__ import annotations
from dataclasses import dataclass, field

_VALID_TYPES = {"string", "integer", "number", "boolean", "array", "object", "null"}


@dataclass
class ValidationReport:
    hint: str
    is_valid: bool
    was_auto_fixed: bool
    issues: list = field(default_factory=list)


def validate_and_fix(endpoint: dict, ground_truth) -> tuple:
    """
    Validates and auto-fixes an LLM-generated endpoint against ground truth.
    Returns (fixed_endpoint, ValidationReport).
    """
    ep     = dict(endpoint)
    issues: list = []
    fixed  = False

    # ── 1. Method & path — ground truth is authoritative ─────────────────────
    if (ep.get("method") or "").upper() != ground_truth.method:
        issues.append(f"Method corrected: '{ep.get('method')}' → '{ground_truth.method}'")
        ep["method"] = ground_truth.method
        fixed = True

    if ep.get("path") != ground_truth.path:
        issues.append(f"Path corrected: '{ep.get('path')}' → '{ground_truth.path}'")
        ep["path"] = ground_truth.path
        fixed = True

    # ── 2. Build / repair input_schema ───────────────────────────────────────
    in_schema = dict(ep.get("input_schema") or {})
    props     = dict(in_schema.get("properties") or {})
    required  = list(in_schema.get("required") or [])

    # 2a. All path params must exist and be required
    for pp in ground_truth.path_params:
        name = pp["name"]
        if not name:
            continue
        if name not in props:
            props[name] = {
                "type":        pp.get("type", "string"),
                "description": pp.get("description") or "Path parameter",
            }
            issues.append(f"Auto-added missing path param: '{name}'")
            fixed = True
        if name not in required:
            required.append(name)
            fixed = True

    # 2b. Add ground-truth query params that LLM omitted
    existing = set(props)
    for qp in ground_truth.query_params:
        name = qp["name"]
        if not name or name in existing:
            continue
        props[name] = {
            "type":        qp.get("type", "string"),
            "description": qp.get("description") or "",
        }
        if qp.get("required") and name not in required:
            required.append(name)
        issues.append(f"Auto-added missing query param: '{name}'")
        fixed = True

    # 2c. Coerce invalid JSON Schema types
    for prop_name, prop_val in props.items():
        if isinstance(prop_val, dict):
            ptype = prop_val.get("type")
            if ptype and ptype not in _VALID_TYPES:
                props[prop_name]["type"] = "string"
                issues.append(f"Invalid type '{ptype}' on '{prop_name}' → coerced to string")
                fixed = True

    # 2d. Warn when POST/PUT/PATCH has no body schema at all
    if ep.get("method") in ("POST", "PUT", "PATCH") and not props:
        issues.append(f"Warning: {ep['method']} endpoint has no input schema")

    # 2e. Fall back to ground-truth requestBody schema if LLM left properties empty
    if not props and ground_truth.body_schema:
        ep["input_schema"] = ground_truth.body_schema
        issues.append("Used ground-truth requestBody schema as input_schema")
        fixed = True
    elif props or required:
        ep["input_schema"] = {"type": "object", "properties": props, "required": required}

    # Hard errors are anything that isn't an auto-add or warning
    hard_issues = [
        i for i in issues
        if not i.startswith(("Auto-added", "Used ground", "Warning"))
    ]

    hint = f"{ep.get('method', '')} {ep.get('path', '')}"
    report = ValidationReport(
        hint=hint,
        is_valid=len(hard_issues) == 0,
        was_auto_fixed=fixed,
        issues=issues,
    )
    return ep, report
