import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


APP_ENV = os.getenv("APP_ENV", "dev")
ENV_FILE = Path(__file__).with_name(".env")
ENV_PROFILE_FILE = Path(__file__).with_name(f".env.{APP_ENV}")
ENV_FALLBACK_FILES = (
    Path(__file__).with_name(".env.dev"),
    Path(__file__).with_name(".env.stg"),
    Path(__file__).with_name(".env.prod"),
)


def _env_files_for_settings() -> tuple[Path, ...]:
    """
    Load the common .env file first, then the active profile file if it exists.

    This keeps today's local developer flow working while making the profile
    split explicit and predictable for dev/stg/prod deployments.
    """
    files: list[Path] = [ENV_FILE]
    if ENV_PROFILE_FILE not in files:
        files.append(ENV_PROFILE_FILE)
    for candidate in ENV_FALLBACK_FILES:
        if candidate.exists() and candidate not in files:
            files.append(candidate)
    return tuple(files)


class Settings(BaseSettings):
    openai_api_key: str = "mock"
    mock_llm: bool = False
    database_url: str = "sqlite:///./mcp_hub.db"
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:5173"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    encryption_key: str = ""

    # ── SMTP (Gmail) ──────────────────────────────────────────────────────────
    smtp_host:     str = "smtp.gmail.com"
    smtp_port:     int = 587
    smtp_user:     str = ""   # your Gmail address
    smtp_password: str = ""   # Gmail App Password (not your regular password)

    # ── Google OAuth2 ─────────────────────────────────────────────────────────
    google_client_id:     str = ""
    google_client_secret: str = ""
    google_redirect_uri:  str = "http://localhost:8000/api/auth/google/callback"

    # ── GitHub OAuth2 ────────────────────────────────────────────────────────
    github_client_id:     str = ""
    github_client_secret: str = ""
    github_redirect_uri:  str = "http://localhost:8000/api/auth/github/callback"

    # ── Frontend base URL (for OAuth redirects back to SPA) ───────────────────
    frontend_url: str = "http://localhost:5173"
    data_dir: str = "./data"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800
    run_migrations_on_startup: bool = True
    read_only_mode: bool = False
    max_request_bytes: int = 10 * 1024 * 1024
    allow_private_tool_hosts: bool = False
    csp_policy: str = "default-src 'self'; frame-ancestors 'none'"
    okta_authorize_url: str = ""
    okta_client_id: str = ""
    okta_redirect_uri: str = "http://localhost:8000/api/auth/okta/callback"
    sso_authorize_url: str = ""
    sso_client_id: str = ""
    sso_redirect_uri: str = "http://localhost:8000/api/auth/sso/callback"
    otel_enabled: bool = False
    emergency_stop: bool = False
    dry_run_tools: bool = False
    max_tool_execution_ms: int = 5000

    model_config = SettingsConfigDict(env_file=_env_files_for_settings(), extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
