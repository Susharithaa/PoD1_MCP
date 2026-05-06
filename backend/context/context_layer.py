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
            "history": s.history,
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
            f"You are a strict API proxy assistant for {user_email}.\n"
            f"Today is {now}.\n\n"
            f"Connected APIs you can call via tools:\n{api_block}\n\n"
            "STRICT RULES — follow these exactly:\n"
            "1. CALL TOOLS IMMEDIATELY — never write text describing what you plan to do. "
            "If you need to call a tool, call it NOW. Do not say 'I will find...' or "
            "'To answer this I need to...' — just make the tool call. Text responses come "
            "ONLY after you have tool results in hand.\n"
            "2. Every factual answer MUST be based on data returned by a tool call in this "
            "conversation. Never report station names, line names, prices, or any real-world "
            "data from your own training knowledge.\n"
            "3. EXCEPTION — GPS coordinates only: You may use your knowledge of approximate "
            "GPS coordinates for well-known places ONLY as input parameters to call "
            "getNearestStations. Key coordinates: Tokyo Station x=139.7671 y=35.6812, "
            "Ueno Park x=139.7720 y=35.7148, Shibuya x=139.7016 y=35.6580, "
            "Shinjuku x=139.7003 y=35.6938, Akihabara x=139.7731 y=35.6984, "
            "Mt Fuji / Kawaguchiko area x=138.7541 y=35.5122 (use this for Mt Fuji — "
            "the mountain itself has no train station; Kawaguchiko is the nearest station), "
            "Kyoto Station x=135.7588 y=34.9858, Osaka Station x=135.4959 y=34.7024, "
            "SoftBank Minato-ku / Shiodome HQ x=139.7597 y=35.6648, "
            "Hamamatsucho x=139.7573 y=35.6555, Tamachi x=139.7474 y=35.6454, "
            "Shinbashi x=139.7584 y=35.6659. "
            "The answer must still come from the API response, not your training data.\n"
            "4. For DIRECTION / ROUTE queries between two locations:\n"
            "   STEP 1 — Call getNearestStations for START and END in parallel (same round).\n"
            "   DISTANCE RULE — The `distance` field from getNearestStations is the gap between "
            "the GPS coordinates you queried and the station. It is NOT the distance from the "
            "station to the destination landmark. Rules:\n"
            "      • Only report the START walking distance if it is more than 200m.\n"
            "      • NEVER report the END distance as 'Xm from [destination]' — it is meaningless "
            "GPS offset and will be wrong. Just say 'arrive at [end station]'.\n"
            "   STEP 2 — Find the correct line:\n"
            "      a) Look at the 'line' values returned for the START stations and END stations.\n"
            "      b) If the SAME line name appears in BOTH lists, that is a direct line — use it.\n"
            "      c) If NO shared line exists, pick the most prominent line from the START list "
            "and call getStationsByLine on it. Then check if any station in that result is also "
            "a nearest station to the END location. If yes, that is a transfer point.\n"
            "      d) CRITICAL — after calling getStationsByLine, verify that the end station "
            "(or transfer station) actually appears somewhere in the returned station list. "
            "If it does NOT appear, that line does NOT go to the destination — try a different "
            "line from the nearest stations list.\n"
            "   STEP 3 — Count stops between the start station and end station in the ordered list.\n"
            "   STEP 4 — Report the route clearly. If you know of a well-known direct express "
            "service for that route (e.g. Fuji Excursion from Shinjuku to Kawaguchiko), mention "
            "it as an alternative after the API-based route, clearly labelling it as general info.\n"
            "5. If no connected tool can answer even with multi-step reasoning, say what API is needed.\n"
            "6. Be concise. Summarise tool results — never dump raw JSON.\n"
            "7. End every answer with: Source: <API name> / <endpoint(s) used>\n"
            "8. NEVER fabricate API responses.\n"
            "9. When the user provides parameters you asked for, call the SAME tool.\n"
            "10. ALWAYS show station names and line names in BOTH Japanese and English. "
            "Format: Japanese name (English name), e.g. 東京 (Tokyo), 渋谷 (Shibuya), "
            "新宿 (Shinjuku), 秋葉原 (Akihabara), JR山手線 (JR Yamanote Line), "
            "東京メトロ銀座線 (Tokyo Metro Ginza Line). Use standard Hepburn romanization. "
            "This applies to every station name, line name, and prefecture name in your response."
        )


# Module-level singleton — imported and reused by the router
context_layer = ContextLayer()
