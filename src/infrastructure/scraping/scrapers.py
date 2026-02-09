from __future__ import annotations

from src.domain.interfaces.scrapers import ICuponsScraper, IOffersScraper, IRelampagoScraper, SeenChecker
from src.infrastructure.scraping.ml_playwright_scraper import MercadoLivrePlaywrightScraper


class OfertasScraper(IOffersScraper):
    def __init__(self, engine: MercadoLivrePlaywrightScraper):
        self.engine = engine

    async def collect_links(
        self,
        max_produtos: int,
        seen_checker: SeenChecker | None = None,
        start_url: str | None = None,
    ) -> list[str]:
        return await self.engine.collect_offer_links(
            "ofertas",
            max_produtos,
            seen_checker=seen_checker,
            start_url=start_url,
        )

    async def extract_product(self, url: str) -> dict:
        return await self.engine.extract_offer_product(url, include_tempo=False)


class OfertasRelampagoScraper(IRelampagoScraper):
    def __init__(self, engine: MercadoLivrePlaywrightScraper):
        self.engine = engine

    async def collect_links(
        self,
        max_produtos: int,
        seen_checker: SeenChecker | None = None,
        start_url: str | None = None,
    ) -> list[str]:
        return await self.engine.collect_offer_links(
            "ofertas_relampago",
            max_produtos,
            seen_checker=seen_checker,
            start_url=start_url,
        )

    async def extract_product(self, url: str) -> dict:
        return await self.engine.extract_offer_product(url, include_tempo=True)


class CuponsScraper(ICuponsScraper):
    def __init__(self, engine: MercadoLivrePlaywrightScraper):
        self.engine = engine

    async def scrape(self, max_cupons: int) -> list[dict]:
        return await self.engine.scrape_coupons(max_cupons=max_cupons)
