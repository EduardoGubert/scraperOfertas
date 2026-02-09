from __future__ import annotations

import logging

from src.domain.interfaces.cache import ICache
from src.infrastructure.cache.local_json_cache import LocalJsonCache
from src.infrastructure.config.settings import Settings


async def build_cache(settings: Settings, logger: logging.Logger) -> ICache:
    backend = (settings.cache_backend or "redis").lower()
    if backend in {"redis", "auto"}:
        try:
            from src.infrastructure.cache.redis_cache import RedisCache

            cache = RedisCache(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                ssl=settings.redis_ssl,
                ttl_seconds=settings.cache_ttl_seconds,
                key_prefix=settings.cache_key_prefix,
            )
            await cache.redis.ping()
            logger.info("Cache backend ativo: redis")
            return cache
        except Exception as exc:
            if backend == "redis":
                logger.warning(f"Falha ao conectar Redis, fallback para JSON local: {exc}")
            else:
                logger.info("Redis indisponivel; usando cache JSON local")

    logger.info("Cache backend ativo: local_json")
    return LocalJsonCache(
        file_path=settings.cache_json_file,
        ttl_seconds=settings.cache_ttl_seconds,
        key_prefix=settings.cache_key_prefix,
    )
