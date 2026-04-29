from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Text, DateTime, JSON  # String used for user_id below
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String, nullable=True)          # DOC | CHAT
    state: Mapped[str] = mapped_column(String, default="INIT")

    # ── inputs ───────────────────────────────────────────────────────────────
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── agent outputs (each step writes its result here) ─────────────────────
    extracted_schema: Mapped[Any] = mapped_column(JSON, nullable=True)
    draft_api: Mapped[Any] = mapped_column(JSON, nullable=True)
    confidence_map: Mapped[Any] = mapped_column(JSON, nullable=True)

    # ── HITL ─────────────────────────────────────────────────────────────────
    human_edits: Mapped[Any] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[Any] = mapped_column(JSON, default=list)

    # ── final output ─────────────────────────────────────────────────────────
    final_api: Mapped[Any] = mapped_column(JSON, nullable=True)
    api_definition_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── multi-tenancy ─────────────────────────────────────────────────────────
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # ── auth credentials (for live API testing, stored per-session) ─────────
    auth_credentials: Mapped[Any] = mapped_column(JSON, nullable=True)

    # ── API live-test results (one entry per endpoint) ───────────────────────
    api_test_results: Mapped[Any] = mapped_column(JSON, nullable=True)

    # ── pre-HITL validation reports (one entry per endpoint, from SchemaAgent) ─
    validation_reports: Mapped[Any] = mapped_column(JSON, nullable=True)

    # ── endpoint coverage: reference (file) vs generated ────────────────────
    coverage_report: Mapped[Any] = mapped_column(JSON, nullable=True)

    # ── observability ────────────────────────────────────────────────────────
    error_log: Mapped[Any] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def log_error(self, step: str, error: str) -> None:
        if self.error_log is None:
            self.error_log = []
        self.error_log = self.error_log + [{"step": step, "error": error,
                                            "at": datetime.now(timezone.utc).isoformat()}]
