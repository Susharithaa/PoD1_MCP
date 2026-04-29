from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="user", nullable=False, server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_provider: Mapped[str] = mapped_column(
        String, default="local", nullable=False, server_default="local"
    )  # "local" | "google" | "github"
    chat_status: Mapped[str] = mapped_column(
        String, default="none", nullable=False, server_default="none"
    )  # "none" | "pending" | "approved" | "rejected"
    credits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
