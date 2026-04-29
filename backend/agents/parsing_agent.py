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

        if not chunks:
            raise ValueError(
                "No API endpoints could be detected in the uploaded document. "
                "Make sure the file contains API documentation with HTTP methods and paths."
            )

        session.extracted_schema = {
            "base_url":  base_info.get("base_url", ""),
            "auth_type": base_info.get("auth_type", "UNKNOWN"),
            "name":      base_info.get("name", ""),
            "_fmt":      fmt,
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
