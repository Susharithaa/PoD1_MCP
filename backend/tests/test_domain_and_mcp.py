"""Tests for the shared remote download path and expense MCP tools."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("OPENAI_API_KEY", "mock")
os.environ.setdefault("ENCRYPTION_KEY", "test-key")

from unittest.mock import MagicMock, patch

from utils.remote_fetch import fetch_remote_text


def test_fetch_remote_text_masks_and_returns_preview():
    fake_response = MagicMock()
    fake_response.headers = {"content-type": "text/plain"}
    fake_response.content = b"hello sk-proj-secret"
    fake_response.text = "hello sk-proj-secret"
    fake_response.raise_for_status.return_value = None

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.get.return_value = fake_response

    with patch("utils.remote_fetch.validate_outbound_url"), patch("utils.remote_fetch.httpx.Client", return_value=fake_client):
        result = fetch_remote_text("https://example.com/file.txt", request_id="req-1")

    assert result.content_type == "text/plain"
    assert result.size == len(fake_response.content)
    assert "[REDACTED]" in result.preview
    fake_client.get.assert_called_once()
