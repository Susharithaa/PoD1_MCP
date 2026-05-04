import logging
from pathlib import Path

try:
    from alembic import command
    from alembic.config import Config
except Exception:  # pragma: no cover - fallback when Alembic is unavailable in tests
    command = None
    Config = None

from config import settings


def run_server_migrations() -> None:
    if not settings.run_migrations_on_startup:
        return
    if command is None or Config is None:
        logging.getLogger(__name__).warning("Alembic unavailable; skipping startup migrations.")
        return
    if settings.database_url.startswith("sqlite"):
        logging.getLogger(__name__).info(
            "Skipping Alembic startup migrations for SQLite; init_db compatibility migrations will run."
        )
        return
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    if not alembic_ini.exists():
        logging.getLogger(__name__).warning("alembic.ini not found; skipping migrations")
        return
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    try:
        command.upgrade(cfg, "head")
    except Exception:
        logging.getLogger(__name__).exception("alembic_upgrade_failed")
