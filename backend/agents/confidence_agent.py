"""ConfidenceAgent — scores each field of the draft API for HITL highlighting."""

import json
from agents.base import BaseAgent
from models.agent_session import AgentSession
from llm.client import chat_json

_META_SYSTEM = """You are an API quality reviewer. Score the top-level fields of this API schema.

Return a JSON object where each key is a field name and the value is:
{"score": 0-100, "status": "HIGH"|"MEDIUM"|"LOW"|"MISSING", "suggestion": "short fix or null"}

Status rules: HIGH>=80, MEDIUM 50-79, LOW<50, MISSING=null/absent.
Evaluate only: name, description, base_url, auth_type.
Return ONLY the JSON object."""


def _score_endpoints(endpoints: list, validation_reports: list) -> dict:
    """Rule-based endpoint scoring, adjusted by pre-HITL validation results."""
    # Build a lookup: hint → report
    report_map: dict = {}
    for r in (validation_reports or []):
        report_map[r.get("hint", "")] = r

    result: dict = {}
    for i, ep in enumerate(endpoints):
        prefix = f"endpoints.{i}"
        hint   = f"{ep.get('method','')} {ep.get('path','')}"
        report = report_map.get(hint, {})
        had_fixes  = report.get("was_auto_fixed", False)
        had_errors = not report.get("is_valid", True)

        # Base scores for required identity fields
        for field_name in ("name", "path", "method", "auth_type"):
            val = ep.get(field_name)
            if not val:
                result[f"{prefix}.{field_name}"] = {
                    "score": 0, "status": "MISSING",
                    "suggestion": f"Add {field_name}",
                }
            else:
                score = 85 if not had_errors else 65
                result[f"{prefix}.{field_name}"] = {
                    "score": score,
                    "status": "HIGH" if score >= 80 else "MEDIUM",
                    "suggestion": None,
                }

        # Input schema
        props = (ep.get("input_schema") or {}).get("properties") or {}
        if not props:
            result[f"{prefix}.input_schema"] = {
                "score": 30, "status": "LOW",
                "suggestion": "Add input parameters",
            }
        else:
            score = 80 if not had_fixes else 65
            result[f"{prefix}.input_schema"] = {
                "score": score,
                "status": "HIGH" if score >= 80 else "MEDIUM",
                "suggestion": "Review auto-fixed parameters" if had_fixes else None,
            }

        # Output schema
        out_props = (ep.get("output_schema") or {}).get("properties") or {}
        if not out_props:
            result[f"{prefix}.output_schema"] = {
                "score": 40, "status": "MEDIUM",
                "suggestion": "Add output schema",
            }
        else:
            result[f"{prefix}.output_schema"] = {
                "score": 80, "status": "HIGH", "suggestion": None,
            }

    return result


class ConfidenceAgent(BaseAgent):
    name = "confidence_agent"

    async def run(self, session: AgentSession) -> AgentSession:
        draft    = session.draft_api or {}
        endpoints = draft.get("endpoints", [])
        reports   = session.validation_reports or []

        meta_prompt = json.dumps(
            {k: draft.get(k) for k in ("name", "description", "base_url", "auth_type")},
            indent=2,
        )
        try:
            meta_scores = await chat_json(_META_SYSTEM, meta_prompt, max_tokens=512)
        except Exception:
            meta_scores = {}

        session.confidence_map = {
            **meta_scores,
            **_score_endpoints(endpoints, reports),
        }
        return session
