from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class ChatGPTConnection(Base):
    __tablename__ = "chatgpt_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    api_definition_id: Mapped[str] = mapped_column(
        String, ForeignKey("api_definitions.id", ondelete="CASCADE")
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)


class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    api_definition_id: Mapped[str] = mapped_column(
        String, ForeignKey("api_definitions.id", ondelete="CASCADE")
    )
    endpoint_name: Mapped[str] = mapped_column(String)
    arguments: Mapped[str] = mapped_column(Text, default="{}")
    result: Mapped[str] = mapped_column(Text, default="")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    called_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
