from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey  # ForeignKey used for both relations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class ApiDefinition(Base):
    __tablename__ = "api_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    visibility: Mapped[str] = mapped_column(String, default="PRIVATE")  # PRIVATE|TEAM|PUBLIC
    version: Mapped[str] = mapped_column(String, default="1.0.0")
    tags: Mapped[Any] = mapped_column(JSON, default=list)
    source_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    endpoints: Mapped[list["ApiEndpoint"]] = relationship(
        "ApiEndpoint", back_populates="definition", cascade="all, delete-orphan"
    )


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    api_definition_id: Mapped[str] = mapped_column(String, ForeignKey("api_definitions.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[str] = mapped_column(String)
    method: Mapped[str] = mapped_column(String)
    input_schema: Mapped[Any] = mapped_column(JSON, nullable=True)
    output_schema: Mapped[Any] = mapped_column(JSON, nullable=True)
    headers: Mapped[Any] = mapped_column(JSON, default=list)
    auth_type: Mapped[str | None] = mapped_column(String, nullable=True)
    auth_credentials: Mapped[Any] = mapped_column(JSON, nullable=True)

    definition: Mapped["ApiDefinition"] = relationship(
        "ApiDefinition", back_populates="endpoints"
    )
