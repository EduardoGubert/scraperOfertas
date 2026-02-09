import asyncio
from unittest.mock import AsyncMock

from src.application.services.deduplication_service import CouponDeduplicationService, OfferDeduplicationService


def test_offer_dedup_service_prefers_database():
    repo = AsyncMock()
    cache = AsyncMock()
    repo.exists_offer = AsyncMock(return_value=True)
    cache.exists = AsyncMock(return_value=False)
    cache.set = AsyncMock()

    service = OfferDeduplicationService(
        repository=repo,
        cache=cache,
        scraper_type="ofertas",
        table_name="ml_ofertas",
    )

    seen = asyncio.run(service.is_seen_by_url("https://produto.mercadolivre.com.br/MLB-123456789-item"))
    assert seen is True
    assert repo.exists_offer.await_count == 1
    assert cache.set.await_count == 1


def test_coupon_dedup_service_checks_db_then_cache():
    repo = AsyncMock()
    cache = AsyncMock()
    repo.exists_coupon = AsyncMock(return_value=False)
    cache.exists = AsyncMock(return_value=True)
    cache.set = AsyncMock()

    service = CouponDeduplicationService(repository=repo, cache=cache)
    seen = asyncio.run(service.is_seen("coupon:abcd"))
    assert seen is True
    assert repo.exists_coupon.await_count == 1
    assert cache.exists.await_count == 1
