from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from config import settings
from utils.masking import mask_sensitive
from utils.ssrf import validate_outbound_url


DEFAULT_REMOTE_FETCH_TIMEOUT_S = 5.0
DEFAULT_PREVIEW_LIMIT = 1000


@dataclass
class RemoteFetchResult:
    url: str
    content_type: str | None
    size: int
    preview: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "content_type": self.content_type,
            "size": self.size,
            "preview": self.preview,
        }


def fetch_remote_text(
    url: str,
    *,
    request_id: str | None = None,
    timeout_s: float = DEFAULT_REMOTE_FETCH_TIMEOUT_S,
    preview_limit: int = DEFAULT_PREVIEW_LIMIT,
) -> RemoteFetchResult:
    validate_outbound_url(url)
    headers = {}
    if request_id:
        headers["X-Request-Id"] = request_id

    with httpx.Client(timeout=timeout_s, follow_redirects=True, verify=not settings.allow_insecure_ssl, headers=headers) as client:
        response = client.get(url)
    response.raise_for_status()

    content_type = response.headers.get("content-type")
    preview = response.text[:preview_limit] if content_type and "text" in content_type else ""
    return RemoteFetchResult(
        url=url,
        content_type=content_type,
        size=len(response.content),
        preview=mask_sensitive(preview),
    )
