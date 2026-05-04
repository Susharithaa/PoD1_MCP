"""Minimal jose compatibility shim for HS256 JWT usage in this app."""

from .jwt import JWTError, decode, encode

__all__ = ["JWTError", "encode", "decode"]
