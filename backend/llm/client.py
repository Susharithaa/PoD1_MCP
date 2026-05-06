"""OpenAI SDK wrapper with gpt-4o and a mock mode for local dev."""

import json
import logging
from openai import AsyncOpenAI, AsyncAzureOpenAI
from config import settings

_client: AsyncOpenAI | None = None

MODEL = "gpt-4o"
log = logging.getLogger(__name__)


def _should_mock() -> bool:
    key = (settings.openai_api_key or "").strip()
    if settings.mock_llm:
        return True
    if not key:
        return True
    placeholder_tokens = {"mock", "sk-...", "sk-proj-...", "replace-with-real-key"}
    if key in placeholder_tokens:
        return True
    if key.startswith("sk-") and len(key) < 20:
        return True
    return False


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if settings.azure_openai_endpoint:
            _client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.effective_openai_key,
                api_version=settings.azure_openai_api_version,
            )
        else:
            _client = AsyncOpenAI(api_key=settings.effective_openai_key)
    return _client


async def chat(system: str, user: str, *, max_tokens: int = 2048) -> str:
    """Single-turn LLM call. Returns raw text response."""
    if _should_mock():
        if not settings.mock_llm:
            log.warning("Falling back to mock LLM mode because OPENAI_API_KEY is missing or placeholder-like.")
        return _mock_response(system, user)

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
    if _should_mock():
        if not settings.mock_llm:
            log.warning("Falling back to mock LLM mode because OPENAI_API_KEY is missing or placeholder-like.")
        raw = _mock_response(system, user)
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

def _mock_response(system: str, prompt: str) -> str:
    s = system.lower()

    # Dispatch by system prompt — reliable regardless of document content
    if "api schema designer" in s:
        # schema_agent._META_SYSTEM: returns API-level metadata
        return json.dumps({
            "name":        "",
            "description": "",
            "base_url":    "",
            "version":     "1.0.0",
            "auth_type":   "NONE",
        })

    if "api schema enricher" in s:
        # schema_agent._ENDPOINT_SYSTEM: enriches a single endpoint
        return json.dumps({
            "name":          "api_endpoint",
            "description":   "API endpoint",
            "path":          "/",
            "method":        "GET",
            "auth_type":     "NONE",
            "input_schema":  {"type": "object", "properties": {}, "required": []},
            "output_schema": {"type": "object", "properties": {}},
            "headers":       [],
        })

    if "list every api endpoint" in s:
        # smart_chunker._INDEX_SYSTEM: returns endpoint index list
        return json.dumps([])

    if "extract the complete definition" in s:
        # smart_chunker._ENDPOINT_SYSTEM: extracts one unstructured endpoint
        return json.dumps({
            "path":             "/",
            "method":           "GET",
            "name":             "api_endpoint",
            "description":      "API endpoint",
            "parameters":       [],
            "response_example": {},
        })

    if "api-level metadata" in s:
        # smart_chunker._BASE_INFO_SYSTEM
        return json.dumps({
            "name":        "",
            "description": "",
            "base_url":    "",
            "auth_type":   "NONE",
        })

    if "api schema consistency reviewer" in s:
        # reconciliation_agent._RECONCILE_SYSTEM
        return json.dumps({"endpoints": []})

    if "api testing expert" in s:
        # api_test_agent._SYSTEM
        return json.dumps({
            "verdict":    "PASS",
            "assessment": "Mock test passed.",
            "issues":     [],
        })

    if "api quality reviewer" in s:
        # confidence_agent._META_SYSTEM
        return json.dumps({
            "name":         {"score": 80, "status": "HIGH",   "suggestion": None},
            "description":  {"score": 60, "status": "MEDIUM", "suggestion": None},
            "base_url":     {"score": 80, "status": "HIGH",   "suggestion": None},
            "auth_type":    {"score": 60, "status": "MEDIUM", "suggestion": None},
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
