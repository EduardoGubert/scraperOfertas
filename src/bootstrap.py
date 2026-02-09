from __future__ import annotations

from contextlib import asynccontextmanager

from src.application.use_cases.run_scraper_job import RunScraperJobUseCase
from src.infrastructure.cache.factory import build_cache
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.logging.logger import setup_logging
from src.infrastructure.persistence.postgres import PostgresConnection
from src.infrastructure.persistence.repositories import PostgresCouponRepository, PostgresOfferRepository
from src.infrastructure.scraping.ml_playwright_scraper import MercadoLivrePlaywrightScraper


class AppContainer:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.logger = setup_logging(log_name="scraperofertas", filename_prefix="scraperofertas")

        self.db = PostgresConnection(self.settings)
        self.cache = None

        self.offer_repository = None
        self.coupon_repository = None
        self.job_use_case = None

    async def __aenter__(self) -> "AppContainer":
        await self.db.connect()
        self.cache = await build_cache(self.settings, self.logger)

        self.offer_repository = PostgresOfferRepository(self.db)
        self.coupon_repository = PostgresCouponRepository(self.db)
        self.job_use_case = RunScraperJobUseCase(
            logger=self.logger,
            offer_repository=self.offer_repository,
            coupon_repository=self.coupon_repository,
            cache=self.cache,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.cache is not None:
            await self.cache.close()
        await self.db.close()

    def engine_factory(self, headless: bool, max_produtos: int) -> MercadoLivrePlaywrightScraper:
        return MercadoLivrePlaywrightScraper(
            headless=headless,
            wait_ms=self.settings.scraper_wait_ms,
            max_produtos=max_produtos,
            user_data_dir=self.settings.browser_data_dir,
        )


@asynccontextmanager
async def build_container(settings: Settings | None = None):
    async with AppContainer(settings=settings) as container:
        yield container
