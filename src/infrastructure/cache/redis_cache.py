from __future__ import annotations

from redis.asyncio import Redis

from src.domain.interfaces.cache import ICache


class RedisCache(ICache):
    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        password: str | None,
        ssl: bool,
        ttl_seconds: int,
        key_prefix: str = "scraperofertas",
    ):
        self.redis = Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            decode_responses=True,
        )
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

    def _qualify(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(self._qualify(key)))

    async def set(self, key: str) -> None:
        await self.redis.set(self._qualify(key), "1", ex=self.ttl_seconds)

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._qualify(key))

    async def close(self) -> None:
        await self.redis.aclose()
