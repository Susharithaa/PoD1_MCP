"""Tests: credential encryption / decryption round-trip."""
import pytest
from utils.encryption import encrypt_creds, decrypt_creds


def test_encrypt_decrypt_roundtrip():
    creds = {"type": "bearer", "token": "super-secret-token"}
    encrypted = encrypt_creds(creds)
    assert encrypted != creds               # must be transformed
    assert "_enc" in encrypted              # encrypted envelope
    assert "super-secret-token" not in str(encrypted)  # token must not be plain
    decrypted = decrypt_creds(encrypted)
    assert decrypted == creds


def test_none_creds_passthrough():
    assert encrypt_creds(None) is None
    assert decrypt_creds(None) is None


def test_none_type_not_encrypted():
    creds = {"type": "none"}
    result = encrypt_creds(creds)
    assert result == creds  # no-op for "none" auth


def test_unencrypted_passthrough():
    """Existing unencrypted dicts (no _enc key) pass through decrypt unchanged."""
    plain = {"type": "bearer", "token": "tok"}
    assert decrypt_creds(plain) == plain


def test_all_auth_types_survive_roundtrip():
    samples = [
        {"type": "basic",         "username": "user", "password": "pw"},
        {"type": "bearer",        "token": "tok"},
        {"type": "api_key",       "header_name": "X-API-Key", "value": "key123"},
        {"type": "api_key_query", "param_name": "apikey", "value": "key123"},
        {"type": "oauth2",        "client_id": "id", "client_secret": "secret", "token_url": "https://auth.example.com"},
    ]
    for creds in samples:
        assert decrypt_creds(encrypt_creds(creds)) == creds


def test_encrypt_basic_auth():
    creds = {"type": "basic", "username": "admin", "password": "s3cr3t"}
    enc = encrypt_creds(creds)
    assert "admin" not in str(enc)
    assert "s3cr3t" not in str(enc)
    assert decrypt_creds(enc) == creds
