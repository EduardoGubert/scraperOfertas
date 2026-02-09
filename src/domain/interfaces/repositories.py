from __future__ import annotations

from typing import Protocol

from src.domain.entities.coupons import CouponEntity
from src.domain.entities.offers import OfferEntity


class IOfferRepository(Protocol):
    async def exists_offer(self, table: str, chave_dedupe: str, mlb_id: str | None) -> bool:
        ...

    async def upsert_offer(self, table: str, offer: OfferEntity, include_tempo: bool = False) -> tuple[int, bool]:
        ...

    async def get_table_stats(self, table: str) -> dict[str, int]:
        ...


class ICouponRepository(Protocol):
    async def exists_coupon(self, chave_dedupe: str) -> bool:
        ...

    async def upsert_coupon(self, coupon: CouponEntity) -> tuple[int, bool]:
        ...

    async def get_table_stats(self) -> dict[str, int]:
        ...
