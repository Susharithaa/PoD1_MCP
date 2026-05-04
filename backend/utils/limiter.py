"""Shared rate limiter instance.

SlowAPI is preferred, but the app should still boot when it is absent.
"""

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
except Exception:  # pragma: no cover - fallback for lean dev environments
    class _NoopLimiter:
        def limit(self, *_args, **_kwargs):
            def decorator(fn):
                return fn
            return decorator

    limiter = _NoopLimiter()
