import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError, jwt

from config import settings
from database import SessionLocal
from models.operational import AuditLog
from models.user import User
from utils.masking import mask_sensitive
from utils.safety import is_emergency_stop_enabled

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(mask_sensitive(payload), default=str)


class ReadableFormatter(logging.Formatter):
    LEVEL_COLORS = {
        "DEBUG":    "",
        "INFO":     "",
        "WARNING":  "⚠ ",
        "ERROR":    "✖ ",
        "CRITICAL": "✖ ",
    }

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        prefix = self.LEVEL_COLORS.get(record.levelname, "")
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return f"{ts}  {prefix}{msg}"


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ReadableFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "openai", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def emit_audit(
    action: str,
    *,
    user: Any = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    request: Request | None = None,
) -> None:
    try:
        with SessionLocal() as db:
            db.add(AuditLog(
                id=str(uuid.uuid4()),
                actor_user_id=getattr(user, "id", None),
                actor_email=getattr(user, "email", None),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id_ctx.get(),
                ip_address=request.client.host if request and request.client else None,
                metadata_json=mask_sensitive(metadata or {}),
            ))
            db.commit()
    except Exception:
        logging.getLogger(__name__).exception("failed_to_write_audit_log")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            content_length = int(request.headers.get("content-length") or "0")
            if settings.max_request_bytes and content_length > settings.max_request_bytes:
                return JSONResponse({"detail": "Request body too large"}, status_code=413)
            if settings.read_only_mode and request.method not in {"GET", "HEAD", "OPTIONS"}:
                if not request.url.path.startswith(("/health", "/api/auth/login", "/api/auth/verify-otp")):
                    return JSONResponse({"detail": "Read-only mode is enabled"}, status_code=423)
            if is_emergency_stop_enabled() and request.method not in {"GET", "HEAD", "OPTIONS"}:
                allowed = (
                    "/health",
                    "/api/auth/login",
                    "/api/auth/verify-otp",
                    "/api/admin/system-controls",
                )
                if not request.url.path.startswith(allowed):
                    return JSONResponse({"detail": "Emergency stop is enabled"}, status_code=423)
            response = await call_next(request)
            if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.url.path.startswith("/api/admin/audit"):
                _audit_http_request(request, response.status_code)
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logging.getLogger("request").info(
                "HTTP %s %s  →  %dms",
                request.method, request.url.path, elapsed_ms,
            )
            request_id_ctx.reset(token)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["content-security-policy"] = settings.csp_policy
        if request.url.scheme == "https":
            response.headers["strict-transport-security"] = "max-age=31536000; includeSubDomains"
        return response


def _audit_http_request(request: Request, status_code: int) -> None:
    actor_user_id = None
    actor_email = None
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        raw = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(raw, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            actor_user_id = payload.get("sub")
        except JWTError:
            actor_user_id = None
    try:
        with SessionLocal() as db:
            if actor_user_id:
                user = db.get(User, actor_user_id)
                actor_email = user.email if user else None
            db.add(AuditLog(
                id=str(uuid.uuid4()),
                actor_user_id=actor_user_id,
                actor_email=actor_email,
                action=f"http.{request.method.lower()}",
                resource_type="http_request",
                resource_id=request.url.path,
                request_id=request_id_ctx.get(),
                ip_address=request.client.host if request.client else None,
                metadata_json={"path": request.url.path, "status_code": status_code},
            ))
            db.commit()
    except Exception:
        logging.getLogger(__name__).exception("failed_to_write_http_audit")
