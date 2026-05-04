"""Minimal aiofiles compatibility shim for test environments.

The real dependency is used in production, but the repo's test environment
may not have it installed. This module provides the small async file API that
the upload router needs.
"""

from __future__ import annotations

import asyncio
import builtins
from pathlib import Path
from typing import Any


class _AsyncFile:
    def __init__(self, path: str | Path, mode: str, *args: Any, **kwargs: Any):
        self._path = path
        self._mode = mode
        self._args = args
        self._kwargs = kwargs
        self._fh = None

    async def __aenter__(self):
        self._fh = await asyncio.to_thread(builtins.open, self._path, self._mode, *self._args, **self._kwargs)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._fh is not None:
            await asyncio.to_thread(self._fh.close)
        self._fh = None
        return False

    async def read(self, *args: Any, **kwargs: Any):
        return await asyncio.to_thread(self._fh.read, *args, **kwargs)

    async def write(self, data: Any):
        return await asyncio.to_thread(self._fh.write, data)


def open(file: str | Path, mode: str = "r", *args: Any, **kwargs: Any):
    return _AsyncFile(file, mode, *args, **kwargs)
