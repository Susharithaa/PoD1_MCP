"""A small, runnable FastAPI example for MCP Hub manual testing.

Run it locally with:
    uvicorn testing.sample_fastapi_app:app --reload --port 9001

Then use it as the base URL in Chat Builder:
    http://localhost:9001
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI
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
