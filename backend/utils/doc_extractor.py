"""
Extract plain text from any supported file format.
Returns (text, fmt) where fmt is: openapi_json | openapi_yaml | postman | text
"""

import json
import os
import yaml


def extract(file_path: str) -> tuple[str, str]:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".json",):
        return _handle_json(file_path)
    if ext in (".yaml", ".yml"):
        return _handle_yaml(file_path)
    if ext == ".pdf":
        return _handle_pdf(file_path), "text"
    if ext in (".docx",):
        return _handle_docx(file_path), "text"
    # .txt .md .html and anything else
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    # If the file looks like JSON (e.g. api-1.json saved as .txt),
    # try structured detection before falling back to the LLM unstructured path.
    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(raw)
            fmt = _detect_structured_format(data)
            if fmt != "text":
                return raw, fmt
        except (json.JSONDecodeError, TypeError, ValueError):
            data = _attempt_json_repair(raw)
            if data is not None:
                fmt = _detect_structured_format(data)
                if fmt != "text":
                    return json.dumps(data), fmt
    return raw, "text"


# ── Format handlers ────────────────────────────────────────────────────────────

def _handle_json(path: str) -> tuple[str, str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
        fmt = _detect_structured_format(data)
        return raw, fmt
    except json.JSONDecodeError:
        data = _attempt_json_repair(raw)
        if data is not None:
            fmt = _detect_structured_format(data)
            if fmt != "text":
                return json.dumps(data), fmt
        return raw, "text"


class _YamlLoader(yaml.SafeLoader):
    """SafeLoader extended to tolerate YAML 1.1 value-indicator tags (= nodes)."""

yaml.add_constructor(
    "tag:yaml.org,2002:value",
    lambda loader, node: loader.construct_scalar(node),
    Loader=_YamlLoader,
)


def _handle_yaml(path: str) -> tuple[str, str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    try:
        data = yaml.load(raw, Loader=_YamlLoader)  # noqa: S506
        fmt = _detect_structured_format(data)
        return json.dumps(data, indent=2, default=str), fmt.replace("yaml", "json")
    except Exception:
        return raw, "text"


def _handle_pdf(path: str) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p for p in pages if p.strip())
    except Exception as e:
        return f"[PDF extraction failed: {e}]"


def _handle_docx(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return f"[DOCX extraction failed: {e}]"


def _attempt_json_repair(raw: str) -> dict | None:
    """
    Try to salvage truncated JSON by closing any unclosed brackets/braces.
    Returns a parsed dict/list on success, None if repair fails.
    """
    stack = []
    in_string = False
    escape_next = False

    for ch in raw:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append("}" if ch == "{" else "]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()

    if not stack:
        return None  # already valid or unfixable structural mismatch

    # Strip trailing partial tokens (commas, incomplete keys) before closing
    trimmed = raw.rstrip()
    while trimmed and trimmed[-1] in (",", ":"):
        trimmed = trimmed[:-1].rstrip()

    repaired = trimmed + "".join(reversed(stack))
    try:
        return json.loads(repaired)
    except (json.JSONDecodeError, ValueError):
        return None


def _detect_structured_format(data: dict) -> str:
    if not isinstance(data, dict):
        return "text"
    # OpenAPI 3.x
    if "openapi" in data and "paths" in data:
        return "openapi_json"
    # Swagger 2.x
    if "swagger" in data and "paths" in data:
        return "openapi_json"
    # Postman Collection v2/v2.1
    if "info" in data and "item" in data:
        info = data.get("info", {})
        if "postman" in str(info.get("schema", "")).lower():
            return "postman"
    return "text"
