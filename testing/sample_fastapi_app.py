"""A small, runnable FastAPI example for MCP Hub manual testing.

Run it locally with:
    uvicorn testing.sample_fastapi_app:app --reload --port 9001

Then use it as the base URL in Chat Builder:
    http://localhost:9001
"""

from datetime import datetime, timezone

from fastapi import FastAPI


app = FastAPI(
    title="Sample MCP Demo API",
    description="A tiny API with predictable endpoints for MCP Hub testing.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "sample-fastapi-app"}


@app.get("/weather")
def weather(city: str = "Chennai"):
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
