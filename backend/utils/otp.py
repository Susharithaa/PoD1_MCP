"""
In-memory OTP store with 10-minute expiry.
Keyed by email. One live OTP per email at a time.
"""
from __future__ import annotations
import random
import string
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

_OTP_EXPIRY_MINUTES = 10
_OTP_LENGTH = 6


@dataclass
class _OTPEntry:
    code: str
    expires_at: datetime
    attempts: int = 0

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def is_exhausted(self) -> bool:
        return self.attempts >= 5


class OTPStore:
    def __init__(self):
        self._store: dict[str, _OTPEntry] = {}

    def generate(self, email: str) -> str:
        code = "".join(random.choices(string.digits, k=_OTP_LENGTH))
        self._store[email.lower()] = _OTPEntry(
            code=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=_OTP_EXPIRY_MINUTES),
        )
        return code

    def verify(self, email: str, code: str) -> tuple[bool, str]:
        """Returns (success, error_message)."""
        entry = self._store.get(email.lower())
        if not entry:
            return False, "No OTP requested for this email"
        if entry.is_expired():
            del self._store[email.lower()]
            return False, "OTP has expired — please login again"
        if entry.is_exhausted():
            del self._store[email.lower()]
            return False, "Too many incorrect attempts — please login again"
        entry.attempts += 1
        if entry.code != code.strip():
            return False, f"Incorrect OTP ({5 - entry.attempts} attempts remaining)"
        del self._store[email.lower()]
        return True, ""

    def invalidate(self, email: str):
        self._store.pop(email.lower(), None)


otp_store = OTPStore()
