"""A small, runnable FastAPI example for MCP Hub manual testing.

Run it locally with:
    uvicorn testing.sample_fastapi_app:app --reload --port 9001

Then use it as the base URL in Chat Builder:
    http://localhost:9001
"""

import os
import base64
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Security, Query
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
    APIKeyHeader,
    APIKeyQuery,
    OAuth2PasswordBearer,
)
from pydantic import BaseModel, Field

try:
    from openai import AsyncAzureOpenAI
except Exception:  # pragma: no cover - keeps the demo runnable without openai installed
    AsyncAzureOpenAI = None


app = FastAPI(
    title="Sample MCP Demo API",
    description="A tiny API with predictable endpoints for MCP Hub testing.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Auth scheme definitions
# ---------------------------------------------------------------------------

basic_scheme = HTTPBasic(auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query_scheme = APIKeyQuery(name="api_key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

# Dummy credentials — good enough for MCP Hub testing
VALID_USERNAME = "testuser"
VALID_PASSWORD = "testpass"
VALID_BEARER_TOKEN = "mcp-test-bearer-token"
VALID_API_KEY = "mcp-test-api-key-12345"
VALID_OAUTH_TOKEN = "mcp-test-oauth-token"


# ---------------------------------------------------------------------------
# Auth validators
# ---------------------------------------------------------------------------

def verify_basic(credentials: HTTPBasicCredentials = Depends(basic_scheme)):
    if not credentials or credentials.username != VALID_USERNAME or credentials.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid Basic Auth credentials",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username


def verify_bearer(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials or credentials.credentials != VALID_BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer token")
    return credentials.credentials


def verify_api_key_header(api_key: str = Security(api_key_header_scheme)):
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key in header")
    return api_key


def verify_api_key_query(api_key: str = Security(api_key_query_scheme)):
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key in query param")
    return api_key


def verify_oauth2(token: str = Depends(oauth2_scheme)):
    if token != VALID_OAUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing OAuth2 token")
    return token


# ---------------------------------------------------------------------------
# Existing endpoints (no auth)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


@app.get("/health")
def health():
    return {"status": "ok", "service": "sample-fastapi-app"}


@app.get("/weather/{city}")
def weather(city: str):
    return {
        "city": city,
        "temperature_c": 29.5,
        "condition": "Clear",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/forecast/{city}")
def forecast(city: str):
    return {
        "city": city,
        "daily": [
            {"day": "Mon", "summary": "Warm and clear", "high_c": 31, "low_c": 26},
            {"day": "Tue", "summary": "Cloudy", "high_c": 30, "low_c": 25},
        ],
    }


@app.get("/summary/{city}")
def summary(city: str):
    return {
        "city": city,
        "summary": f"{city} is warm and clear with light winds today.",
        "recommendation": "A light cotton outfit and water bottle are a good idea.",
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    api_key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
    endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_BASE_URL") or "").strip().rstrip("/")
    api_version = (os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview").strip()
    deployment = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()

    if not api_key or not endpoint or not deployment:
        return {
            "status": "mock",
            "message": req.message,
            "response": "Azure OpenAI is not configured in the environment.",
        }

    if AsyncAzureOpenAI is None:
        return {
            "status": "mock",
            "message": req.message,
            "response": "openai package is not available in this environment.",
        }

    client = AsyncAzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )
    completion = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a concise helper for MCP Hub sample testing."},
            {"role": "user", "content": req.message},
        ],
    )
    answer = completion.choices[0].message.content or ""
    return {
        "status": "ok",
        "model": deployment,
        "message": req.message,
        "response": answer,
    }


@app.post("/reports")
def create_report(payload: dict):
    return {
        "status": "created",
        "received": payload,
        "id": f"rep-{abs(hash(str(payload))) % 10000:04d}",
    }


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    return {
        "id": report_id,
        "title": "Sample report",
        "status": "ready",
        "items": [
            {"name": "expense", "amount": 42},
            {"name": "travel", "amount": 18},
        ],
    }


# ---------------------------------------------------------------------------
# Auth testing endpoints
# ---------------------------------------------------------------------------

@app.get("/auth/none", tags=["Auth Testing"])
def auth_none():
    """No authentication required."""
    return {"auth_type": "none", "status": "ok", "message": "Access granted without authentication"}


@app.get("/auth/basic", tags=["Auth Testing"])
def auth_basic(username: str = Depends(verify_basic)):
    """Basic Auth — requires Authorization: Basic <base64(user:pass)>
    Valid credentials: testuser / testpass
    """
    return {"auth_type": "basic", "status": "ok", "authenticated_as": username}


@app.get("/auth/bearer", tags=["Auth Testing"])
def auth_bearer(token: str = Depends(verify_bearer)):
    """Bearer Token — requires Authorization: Bearer mcp-test-bearer-token"""
    return {"auth_type": "bearer", "status": "ok", "token_preview": token[:10] + "..."}


@app.get("/auth/api-key-header", tags=["Auth Testing"])
def auth_api_key_header(api_key: str = Depends(verify_api_key_header)):
    """API Key via Header — requires X-API-Key: mcp-test-api-key-12345"""
    return {"auth_type": "api_key_header", "status": "ok", "key_preview": api_key[:8] + "..."}


@app.get("/auth/api-key-query", tags=["Auth Testing"])
def auth_api_key_query(api_key: str = Depends(verify_api_key_query)):
    """API Key via Query Param — requires ?api_key=mcp-test-api-key-12345"""
    return {"auth_type": "api_key_query", "status": "ok", "key_preview": api_key[:8] + "..."}


@app.post("/auth/token", tags=["Auth Testing"])
def oauth2_token(username: str = Query(...), password: str = Query(...)):
    """OAuth2 token endpoint — POST /auth/token?username=testuser&password=testpass
    Returns a bearer token to use with /auth/oauth2.
    """
    if username != VALID_USERNAME or password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": VALID_OAUTH_TOKEN,
        "token_type": "bearer",
    }


@app.get("/auth/oauth2", tags=["Auth Testing"])
def auth_oauth2(token: str = Depends(verify_oauth2)):
    """OAuth2 Client — first get a token from POST /auth/token, then pass it as Bearer."""
    return {"auth_type": "oauth2", "status": "ok", "token_preview": token[:10] + "..."}


# ---------------------------------------------------------------------------
# Auth test summary
# ---------------------------------------------------------------------------

@app.get("/auth/info", tags=["Auth Testing"])
def auth_info():
    """Returns the valid test credentials for all auth types."""
    return {
        "none": {"endpoint": "/auth/none", "credentials": "not required"},
        "basic_auth": {
            "endpoint": "/auth/basic",
            "username": VALID_USERNAME,
            "password": VALID_PASSWORD,
            "header_example": f"Authorization: Basic {base64.b64encode(f'{VALID_USERNAME}:{VALID_PASSWORD}'.encode()).decode()}",
        },
        "bearer_token": {
            "endpoint": "/auth/bearer",
            "token": VALID_BEARER_TOKEN,
            "header_example": f"Authorization: Bearer {VALID_BEARER_TOKEN}",
        },
        "api_key_header": {
            "endpoint": "/auth/api-key-header",
            "api_key": VALID_API_KEY,
            "header_example": f"X-API-Key: {VALID_API_KEY}",
        },
        "api_key_query_param": {
            "endpoint": "/auth/api-key-query",
            "api_key": VALID_API_KEY,
            "query_example": f"/auth/api-key-query?api_key={VALID_API_KEY}",
        },
        "oauth2_client": {
            "token_endpoint": "/auth/token",
            "protected_endpoint": "/auth/oauth2",
            "step1": f"POST /auth/token?username={VALID_USERNAME}&password={VALID_PASSWORD}",
            "step2": f"GET /auth/oauth2 with Authorization: Bearer {VALID_OAUTH_TOKEN}",
        },
    }
