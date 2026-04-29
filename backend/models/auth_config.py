from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AuthConfig(Base):
    __tablename__ = "auth_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    api_definition_id: Mapped[str] = mapped_column(String)
    auth_type: Mapped[str] = mapped_column(String)   # API_KEY | BEARER | BASIC | OAUTH2 | NONE
    secret_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    header_name: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
