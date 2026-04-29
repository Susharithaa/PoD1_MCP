from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import settings


def _make_engine():
    url = settings.database_url
    kwargs: dict = {"echo": False}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            from sqlalchemy.pool import StaticPool
            kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import agent_session, api_definition, auth_config, chatgpt_connection, user, token_usage  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """Add columns introduced after initial schema creation."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    def _add_col(table: str, col: str, col_type: str):
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))

    # users
    if "users" in tables:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "role" not in user_cols:
            _add_col("users", "role", "TEXT NOT NULL DEFAULT 'user'")
        if "auth_provider" not in user_cols:
            _add_col("users", "auth_provider", "TEXT NOT NULL DEFAULT 'local'")
        if "hashed_password" in user_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL")) if not engine.url.drivername.startswith("sqlite") else None

    # agent_sessions
    if "agent_sessions" in tables:
        session_cols = {c["name"] for c in inspector.get_columns("agent_sessions")}
        for col, col_type in {
            "api_test_results": "TEXT",
            "auth_credentials": "TEXT",
            "user_id":          "TEXT",
        }.items():
            if col not in session_cols:
                _add_col("agent_sessions", col, col_type)

    # api_endpoints
    if "api_endpoints" in tables:
        endpoint_cols = {c["name"] for c in inspector.get_columns("api_endpoints")}
        if "auth_credentials" not in endpoint_cols:
            _add_col("api_endpoints", "auth_credentials", "TEXT")

    # api_definitions
    if "api_definitions" in tables:
        def_cols = {c["name"] for c in inspector.get_columns("api_definitions")}
        if "user_id" not in def_cols:
            _add_col("api_definitions", "user_id", "TEXT")

    # chatgpt_connections
    if "chatgpt_connections" in tables:
        conn_cols = {c["name"] for c in inspector.get_columns("chatgpt_connections")}
        if "user_id" not in conn_cols:
            _add_col("chatgpt_connections", "user_id", "TEXT")
