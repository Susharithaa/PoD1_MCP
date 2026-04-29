"""SchemaValidator — rule-based post-HITL validation. No LLM call needed."""

from urllib.parse import urlparse
from agents.base import BaseAgent
from models.agent_session import AgentSession

VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
VALID_AUTH    = {"BEARER", "API_KEY", "BASIC", "OAUTH2", "NONE"}


class SchemaValidator(BaseAgent):
    name = "schema_validator"

    async def run(self, session: AgentSession) -> AgentSession:
        api = session.final_api or session.draft_api or {}
        errors: list[str] = []

        # top-level required fields
        if not api.get("name", "").strip():
            errors.append("API name is required.")
        if not api.get("base_url", "").strip():
            errors.append("base_url is required.")
        else:
            try:
                p = urlparse(api["base_url"])
                if p.scheme not in ("http", "https"):
                    errors.append("base_url must start with http:// or https://")
            except Exception:
                errors.append("base_url is not a valid URL.")

        endpoints = api.get("endpoints", [])
        if not endpoints:
            errors.append("At least one endpoint is required.")

        for i, ep in enumerate(endpoints):
            prefix = f"endpoints[{i}]"
            if not ep.get("path", "").startswith("/"):
                errors.append(f"{prefix}.path must start with '/'.")
            method = ep.get("method", "").upper()
            if method not in VALID_METHODS:
                errors.append(f"{prefix}.method must be one of {VALID_METHODS}.")
            if not ep.get("name", "").strip():
                errors.append(f"{prefix}.name is required.")
            auth = ep.get("auth_type", "NONE").upper()
            if auth not in VALID_AUTH:
                errors.append(f"{prefix}.auth_type must be one of {VALID_AUTH}.")

        session.validation_errors = errors
        return session
