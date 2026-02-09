from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol


SeenChecker = Callable[[str], Awaitable[bool]]


class IOffersScraper(Protocol):
    async def collect_links(
        self,
        max_produtos: int,
        seen_checker: SeenChecker | None = None,
        start_url: str | None = None,
    ) -> list[str]:
        ...

    async def extract_product(self, url: str) -> dict:
        ...


class IRelampagoScraper(Protocol):
    async def collect_links(
        self,
        max_produtos: int,
        seen_checker: SeenChecker | None = None,
        start_url: str | None = None,
    ) -> list[str]:
        ...

    async def extract_product(self, url: str) -> dict:
        ...


class ICuponsScraper(Protocol):
    async def scrape(self, max_cupons: int) -> list[dict]:
        ...
