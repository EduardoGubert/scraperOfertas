from __future__ import annotations

from src.domain.interfaces.cache import ICache
from src.domain.interfaces.repositories import ICouponRepository, IOfferRepository
from src.domain.value_objects.dedupe import CacheKey, build_offer_dedupe_key, extract_mlb_id, normalize_url


class OfferDeduplicationService:
    def __init__(self, repository: IOfferRepository, cache: ICache, scraper_type: str, table_name: str):
        self.repository = repository
        self.cache = cache
        self.scraper_type = scraper_type
        self.table_name = table_name

    async def is_seen_by_url(self, url: str) -> bool:
        normalized_url = normalize_url(url)
        mlb_id = extract_mlb_id(normalized_url)
        dedupe_key = build_offer_dedupe_key(mlb_id=mlb_id, product_id=None, url_original=normalized_url)
        cache_key = CacheKey(self.scraper_type, dedupe_key).value()

        # Fonte de verdade: banco.
        exists_in_db = await self.repository.exists_offer(self.table_name, dedupe_key, mlb_id)
        if exists_in_db:
            await self.cache.set(cache_key)
            return True

        # Cache atua como acelerador complementar.
        return await self.cache.exists(cache_key)

    async def mark_seen(self, dedupe_key: str) -> None:
        await self.cache.set(CacheKey(self.scraper_type, dedupe_key).value())


class CouponDeduplicationService:
    def __init__(self, repository: ICouponRepository, cache: ICache):
        self.repository = repository
        self.cache = cache

    async def is_seen(self, dedupe_key: str) -> bool:
        cache_key = CacheKey("cupons", dedupe_key).value()
        exists_in_db = await self.repository.exists_coupon(dedupe_key)
        if exists_in_db:
            await self.cache.set(cache_key)
            return True
        return await self.cache.exists(cache_key)

    async def mark_seen(self, dedupe_key: str) -> None:
        await self.cache.set(CacheKey("cupons", dedupe_key).value())
