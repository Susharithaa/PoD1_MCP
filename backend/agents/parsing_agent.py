"""
ParsingAgent — extracts API structure from any document.

Structured (OpenAPI / Postman): Option A — chunk at object level, no LLM parsing needed.
Unstructured (PDF / DOCX / TXT): Option C — two-pass LLM extraction.
"""

import json

from agents.base import BaseAgent
from models.agent_session import AgentSession
from utils.doc_extractor import extract
from utils.smart_chunker import chunk


class ParsingAgent(BaseAgent):
    name = "parsing_agent"

    async def run(self, session: AgentSession) -> AgentSession:
        text, fmt = self._get_text_and_format(session)

        base_info, chunks = await chunk(text, fmt)

        session.extracted_schema = {
            "base_url":    base_info.get("base_url", ""),
            "auth_type":   base_info.get("auth_type", "UNKNOWN"),
            "name":        base_info.get("name", ""),
            "description": base_info.get("description", ""),
            "_fmt":        fmt,
            "_doc_type": "api" if chunks else "generic_yaml_or_text",
            "_warnings": [] if chunks else [
                "No API endpoints were detected. The file looks like generic YAML/text rather than API documentation."
            ],
            "_chunks": [
                {"method": c.method, "path": c.path, "hint": c.hint, "content": c.content}
                for c in chunks
            ],
        }
        return session

    def _get_text_and_format(self, session: AgentSession) -> tuple[str, str]:
        if session.file_path:
            return extract(session.file_path)
        return session.raw_input or "", "text"
