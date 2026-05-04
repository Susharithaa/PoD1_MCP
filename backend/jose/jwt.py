from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any


class JWTError(Exception):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def encode(payload: dict[str, Any], secret: str, algorithm: str = "HS256") -> str:
    if algorithm != "HS256":
        raise JWTError(f"Unsupported algorithm: {algorithm}")
    header = {"typ": "JWT", "alg": algorithm}
    body = dict(payload)
    exp = body.get("exp")
    if isinstance(exp, datetime):
        body["exp"] = int(exp.replace(tzinfo=timezone.utc).timestamp())
    header_part = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url(signature)}"


def decode(token: str, secret: str, algorithms: list[str] | None = None) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
    except ValueError as exc:
        raise JWTError("Invalid token") from exc

    header = json.loads(_b64url_decode(header_part))
    if algorithms and header.get("alg") not in algorithms:
        raise JWTError("Unsupported algorithm")
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(signature_part)):
        raise JWTError("Invalid signature")
    payload = json.loads(_b64url_decode(payload_part))
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(datetime.now(timezone.utc).timestamp()):
        raise JWTError("Token expired")
    return payload
