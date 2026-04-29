"""OpenAI SDK wrapper with gpt-4o and a mock mode for local dev."""

import json
from openai import AsyncOpenAI
from config import settings

_client: AsyncOpenAI | None = None

MODEL = "gpt-4o"


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def chat(system: str, user: str, *, max_tokens: int = 2048) -> str:
    """Single-turn LLM call. Returns raw text response."""
    if settings.mock_llm:
        return _mock_response(user)

    client = get_client()
    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return response.choices[0].message.content


async def chat_json(system: str, user: str, *, max_tokens: int = 2048) -> dict:
    """LLM call that enforces a JSON response. Returns parsed dict."""
    if settings.mock_llm:
        raw = _mock_response(user)
        return _parse_json(raw)

    json_system = (
        system
        + "\n\nIMPORTANT: Your entire response must be valid JSON only. "
        "No markdown fences, no explanation — just the JSON object."
    )
    client = get_client()
    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": json_system},
            {"role": "user",   "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return _parse_json(raw)


# ---------------------------------------------------------------------------
# Mock responses for local dev (MOCK_LLM=true)
# ---------------------------------------------------------------------------

def _mock_response(prompt: str) -> str:
    p = prompt.lower()

    if "classify" in p:
        return json.dumps({"mode": "CHAT", "raw_text": prompt})

    if "extract" in p or "parse" in p:
        return json.dumps({
            "base_url": "https://api.example.com",
            "endpoints": [
                {
                    "path": "/sales/report",
                    "method": "GET",
                    "name": "get_sales_report",
                    "description": "Fetch latest sales report",
                    "parameters": [
                        {"name": "start_date", "type": "string", "required": True,
                         "description": "Report start date (YYYY-MM-DD)"},
                        {"name": "end_date", "type": "string", "required": True,
                         "description": "Report end date (YYYY-MM-DD)"},
                        {"name": "region", "type": "string", "required": False,
                         "description": "Filter by region"},
                    ],
                    "response_example": {"total": 0, "currency": "USD", "items": []},
                }
            ],
            "auth_type": "BEARER",
        })

    if "schema" in p or "openapi" in p:
        return json.dumps({
            "name": "Sales Report API",
            "description": "API to fetch sales reports and send summaries",
            "base_url": "https://api.example.com",
            "endpoints": [
                {
                    "name": "get_sales_report",
                    "description": "Fetch latest sales report",
                    "path": "/sales/report",
                    "method": "GET",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "end_date":   {"type": "string", "description": "YYYY-MM-DD"},
                            "region":     {"type": "string", "description": "Optional region filter"},
                        },
                        "required": ["start_date", "end_date"],
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "total":    {"type": "number"},
                            "currency": {"type": "string"},
                            "items":    {"type": "array"},
                        },
                    },
                    "auth_type": "BEARER",
                    "headers": [],
                }
            ],
        })

    if "api test" in p or "verify" in p or "reachable" in p or "status_code" in p:
        return json.dumps({
            "verdict": "PASS",
            "assessment": "API responded as expected. Response structure matches the described schema.",
            "issues": [],
        })

    if "confidence" in p or "score" in p:
        return json.dumps({
            "name":       {"score": 95, "status": "HIGH",    "suggestion": None},
            "base_url":   {"score": 90, "status": "HIGH",    "suggestion": None},
            "path":       {"score": 88, "status": "HIGH",    "suggestion": None},
            "method":     {"score": 95, "status": "HIGH",    "suggestion": None},
            "auth_type":  {"score": 60, "status": "MEDIUM",  "suggestion": "Verify token type"},
            "input_schema": {"score": 75, "status": "MEDIUM","suggestion": "Consider adding pagination"},
            "output_schema": {"score": 50, "status": "LOW",  "suggestion": "Response schema is partial"},
        })

    return json.dumps({"result": "ok"})


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM output, stripping markdown fences if present."""
    text = raw.strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Response was truncated — find the last complete top-level object
        brace_depth = 0
        last_valid = 0
        for i, ch in enumerate(text):
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    last_valid = i + 1
        if last_valid:
            try:
                return json.loads(text[:last_valid])
            except json.JSONDecodeError:
                pass
        raise
