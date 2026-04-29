"""Fernet-based credential encryption. No-op when ENCRYPTION_KEY is unset."""

import base64
import hashlib
import json
from config import settings

try:
    from cryptography.fernet import Fernet, InvalidToken
    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False


def _fernet():
    if not _CRYPTO_OK:
        return None
    key = settings.encryption_key.strip()
    if not key:
        return None
    # Derive a stable 32-byte Fernet key from any string secret
    raw = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_creds(creds: dict | None) -> dict | None:
    """Return encrypted dict suitable for JSON storage, or plain dict if no key."""
    if not creds or creds.get("type", "none") == "none":
        return creds
    f = _fernet()
    if not f:
        return creds
    token = f.encrypt(json.dumps(creds).encode()).decode()
    return {"_enc": token}


def decrypt_creds(stored: dict | None) -> dict | None:
    """Decrypt a previously encrypted dict. Passes through unencrypted dicts."""
    if not stored:
        return None
    if "_enc" not in stored:
        return stored  # stored without encryption key — return as-is
    f = _fernet()
    if not f:
        return None
    try:
        return json.loads(f.decrypt(stored["_enc"].encode()).decode())
    except Exception:
        return None
