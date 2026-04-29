from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from database import init_db
from routers import agent, registry, chatgpt, monitor, auth, social_auth, subscription
from utils.limiter import limiter

app = FastAPI(
    title="MCP Hub API",
    description="API creation, validation, and execution hub powered by AI agents",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(agent.router)
app.include_router(registry.router)
app.include_router(chatgpt.router)
app.include_router(monitor.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "mock_llm": settings.mock_llm}
