from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
except Exception:  # pragma: no cover - fallback when SlowAPI is unavailable
    _rate_limit_exceeded_handler = None
    RateLimitExceeded = None

from config import settings
from database import init_db
from routers import admin_ext, agent, chatgpt, domain, mcp, monitor, registry, security, auth, social_auth, subscription
from utils.limiter import limiter
from utils.migrations import run_server_migrations
from utils.observability import RequestContextMiddleware, configure_logging
from utils.otel import setup_otel

ROOT_DIR = Path(__file__).resolve().parents[1]
TESTING_DIR = ROOT_DIR / "testing"

app = FastAPI(
    title="MCP Hub API",
    description="API creation, validation, and execution hub powered by AI agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.state.limiter = limiter
if RateLimitExceeded and _rate_limit_exceeded_handler:
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestContextMiddleware)


@app.get("/")
def home():
    return {"message": "MCP Hub API Running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(social_auth.router)
app.include_router(subscription.router)
app.include_router(security.router)
app.include_router(agent.router)
app.include_router(registry.router)
app.include_router(chatgpt.router)
app.include_router(monitor.router)
app.include_router(mcp.router)
app.include_router(domain.router)
app.include_router(admin_ext.router)
if TESTING_DIR.exists():
    app.mount("/testing", StaticFiles(directory=str(TESTING_DIR), html=False), name="testing")
setup_otel(app)


@app.on_event("startup")
def startup():
    configure_logging()
    run_server_migrations()
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "mock_llm": settings.mock_llm}
