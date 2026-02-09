from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from src.domain.interfaces.cache import ICache
from src.domain.value_objects.timezone import now_sao_paulo


class LocalJsonCache(ICache):
    def __init__(self, file_path: str, ttl_seconds: int, key_prefix: str = "scraperofertas"):
        self.file_path = Path(file_path)
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self._lock = asyncio.Lock()
        self._data: dict[str, dict[str, Any]] = {"items": {}}
        self._load()

    def _qualify(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def _now_epoch(self) -> int:
        return int(now_sao_paulo().timestamp())

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        try:
            payload = json.loads(self.file_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "items" in payload:
                self._data = payload
            self._cleanup_expired()
        except Exception:
            self._data = {"items": {}}

    def _persist(self) -> None:
        self.file_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _cleanup_expired(self) -> None:
        now_epoch = self._now_epoch()
        stale_keys = [
            key
            for key, item in self._data.get("items", {}).items()
            if item.get("expires_at", 0) <= now_epoch
        ]
        for key in stale_keys:
            self._data["items"].pop(key, None)

    async def exists(self, key: str) -> bool:
        q_key = self._qualify(key)
        async with self._lock:
            self._cleanup_expired()
            item = self._data["items"].get(q_key)
            if not item:
                return False
            return item.get("expires_at", 0) > self._now_epoch()

    async def set(self, key: str) -> None:
        q_key = self._qualify(key)
        async with self._lock:
            now_epoch = self._now_epoch()
            self._data["items"][q_key] = {
                "created_at": now_epoch,
                "expires_at": now_epoch + self.ttl_seconds,
            }
            self._persist()

    async def delete(self, key: str) -> None:
        q_key = self._qualify(key)
        async with self._lock:
            self._data["items"].pop(q_key, None)
            self._persist()

    async def close(self) -> None:
        async with self._lock:
            self._cleanup_expired()
            self._persist()
