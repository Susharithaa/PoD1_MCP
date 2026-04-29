"""
Context Layer — sits between the user message and the LLM.

Responsibilities:
  1. Maintain per-session conversation history (in-memory, keyed by session_id)
  2. Build a rich system prompt from connected APIs + user info
  3. Inject history + system prompt into every LLM call
  4. Trim context window when history grows too long
  5. Auto-expire idle sessions after 2 hours
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Any


_MAX_HISTORY_TURNS = 10   # keep last N user+assistant pairs
_SESSION_TTL_HOURS  = 2


@dataclass
class _Session:
    id: str
    history: list[dict]  = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self):
        self.last_active = datetime.now(timezone.utc)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) - self.last_active > timedelta(hours=_SESSION_TTL_HOURS)


class ContextLayer:
    """
    Singleton-safe: instantiate once at app startup and reuse across requests.
    Thread-safe for asyncio (single-threaded event loop); add a lock if you
    ever move to multi-process workers sharing state via Redis.
    """

    def __init__(self):
        self._sessions: dict[str, _Session] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def build_messages(
        self,
        session_id: str | None,
        user_message: str,
        apis: list,
        user_email: str,
    ) -> tuple[str, list[dict]]:
        """
        Returns (session_id, messages_list_ready_for_openai).
        Creates a new session if session_id is None or expired/unknown.
        """
        self._evict_expired()
        session = self._get_or_create(session_id)
        session.touch()

        system_prompt = self._build_system_prompt(apis, user_email)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._trimmed_history(session))
        messages.append({"role": "user", "content": user_message})

        return session.id, messages

    def save_turn(
        self,
        session_id: str,
        user_message: str,
        turn_messages: list[dict],
    ):
        """
        Persist the completed turn into session history so the next call sees it.
        turn_messages must be the ordered slice of everything added after the user
        message: [assistant+tool_calls?, tool_result?, ..., assistant_final].
        This preserves the exact sequence OpenAI requires.
        """
        session = self._sessions.get(session_id)
        if not session:
            return
        session.history.append({"role": "user", "content": user_message})
        session.history.extend(turn_messages)
        session.touch()

    def clear_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def session_info(self, session_id: str) -> dict | None:
        s = self._sessions.get(session_id)
        if not s:
            return None
        return {
            "session_id": s.id,
            "turns": len([m for m in s.history if m["role"] == "user"]),
            "created_at": s.created_at.isoformat(),
            "last_active": s.last_active.isoformat(),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_create(self, session_id: str | None) -> _Session:
        if session_id and session_id in self._sessions:
            s = self._sessions[session_id]
            if not s.is_expired():
                return s
        new_session = _Session(id=str(uuid4()))
        self._sessions[new_session.id] = new_session
        return new_session

    def _trimmed_history(self, session: _Session) -> list[dict]:
        """Keep only the last N complete turns to avoid token overflow."""
        history = session.history
        # each turn = user + assistant (+ optional tool messages)
        # trim from the front, keeping tail
        max_msgs = _MAX_HISTORY_TURNS * 3  # rough upper bound per turn
        if len(history) > max_msgs:
            history = history[-max_msgs:]
        return history

    def _evict_expired(self):
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]

    @staticmethod
    def _build_system_prompt(apis: list, user_email: str) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        api_lines = []
        for api in apis:
            ep_names = ", ".join(
                ep.name or ep.path for ep in (api.endpoints or [])
            )
            api_lines.append(f"  • {api.name} ({api.base_url}) — endpoints: {ep_names}")

        api_block = "\n".join(api_lines) if api_lines else "  (none connected)"

        return (
            f"You are an intelligent API assistant for {user_email}.\n"
            f"Today is {now}.\n\n"
            f"Connected APIs you can call via tools:\n{api_block}\n\n"
            "Guidelines:\n"
            "- Use the available tools to answer the user's question when relevant.\n"
            "- If a required parameter is missing, ask the user for it — do not guess.\n"
            "- If a tool call fails, explain the error clearly and suggest next steps.\n"
            "- Be concise. Avoid repeating raw JSON to the user — summarise the result.\n"
            "- If no tool exists for a specific part of the user's request, say so explicitly "
            "for that part — do not substitute an unrelated tool or call a tool with empty/wrong "
            "parameters as a fallback. It is better to say 'I have no tool to list X' than to "
            "make a nonsensical tool call.\n"
            "- If the question cannot be answered with the connected APIs, say so directly.\n"
            "- CRITICAL: NEVER fabricate or hallucinate API responses. You may only report data "
            "that was returned by an actual tool call in this conversation. If a tool is not in "
            "the connected APIs list above, you have no access to it — even if it appeared in "
            "earlier conversation turns. Do not invent answers based on memory of past sessions "
            "or prior tool results. Say 'that API is not currently connected' instead.\n"
            "- IMPORTANT: When you previously asked the user for parameters and they are now "
            "providing them, call the SAME tool you identified before — do not switch to a "
            "different tool (e.g. do not call a GET/list tool when you were about to call a "
            "POST/create tool). Re-read the conversation history to confirm which tool you "
            "committed to before asking for parameters.\n"
            "- IMPORTANT: Match the user's intent precisely. If the user says 'create', call "
            "the create/POST tool. If the user says 'list' or 'get', call the list/GET tool. "
            "Never substitute a read operation for a write operation or vice versa."
        )


# Module-level singleton — imported and reused by the router
context_layer = ContextLayer()
