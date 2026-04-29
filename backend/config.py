from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).with_name(".env")


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

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
