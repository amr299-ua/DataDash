# core/cache.py
"""Cache de datasets en memoria, thread-safe. Sin persistencia por diseño."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any


class DatasetCache:
    """Almacena DataFrames procesados y sus derivados, indexados por token opaco.

    Cada entrada expira tras `ttl_seconds` de inactividad. El barrido es perezoso:
    se realiza en cada acceso para evitar threads adicionales.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def put(self, payload: dict[str, Any]) -> str:
        token = uuid.uuid4().hex
        with self._lock:
            self._store[token] = {"payload": payload, "last_access": time.time()}
        return token

    def get(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        with self._lock:
            entry = self._store.get(token)
            if entry is None:
                return None
            if time.time() - entry["last_access"] > self._ttl:
                del self._store[token]
                return None
            entry["last_access"] = time.time()
            return entry["payload"]

    def discard(self, token: str) -> None:
        with self._lock:
            self._store.pop(token, None)

    def sweep(self) -> int:
        now = time.time()
        with self._lock:
            stale = [k for k, v in self._store.items() if now - v["last_access"] > self._ttl]
            for k in stale:
                del self._store[k]
            return len(stale)


dataset_cache = DatasetCache()
