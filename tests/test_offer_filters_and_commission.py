import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.application.use_cases.run_scraper_job import RunScraperJobUseCase
from src.domain.entities.offers import OfferEntity
from src.infrastructure.persistence.repositories import PostgresOfferRepository
from src.infrastructure.scraping.ml_playwright_scraper import MercadoLivrePlaywrightScraper


class _FakeOffersEngine:
    def __init__(self, payload_by_url: dict[str, dict]):
        self.payload_by_url = payload_by_url

    async def collect_offer_links(self, mode, max_produtos, seen_checker=None, start_url=None):  # noqa: ANN001
        return list(self.payload_by_url.keys())[:max_produtos]

    async def extract_offer_product(self, url: str, include_tempo: bool = False) -> dict:  # noqa: ARG002
        return dict(self.payload_by_url[url])


class _FakeAcquireContext:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


class _FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return _FakeAcquireContext(self.conn)


class _FakeConnection:
    def __init__(self):
        self.last_sql = ""
        self.last_params = ()

    async def fetchrow(self, sql: str, *params):
        self.last_sql = sql
        self.last_params = params
        return {"id": 1, "inserted": True}


def test_parse_comissao_percentual_from_text():
    scraper = MercadoLivrePlaywrightScraper()
    assert scraper._parse_percentual("GANHOS 16%") == 16
    assert scraper._parse_percentual("sem percentual") is None


def test_offer_filter_discards_items_below_thresholds():
    logger = logging.getLogger("test.offer.filter")
    offer_repository = AsyncMock()
    offer_repository.ensure_offer_schema_compatibility = AsyncMock(return_value=set())
    offer_repository.exists_offer = AsyncMock(return_value=False)
    offer_repository.upsert_offer = AsyncMock(return_value=(1, True))
    coupon_repository = AsyncMock()
    cache = AsyncMock()
    cache.set = AsyncMock()

    use_case = RunScraperJobUseCase(
        logger=logger,
        offer_repository=offer_repository,
        coupon_repository=coupon_repository,
        cache=cache,
        default_min_desconto_percent=30,
        default_min_comissao_percent=10,
    )

    payload_by_url = {
        "https://produto.mercadolivre.com.br/MLB-111111111-item": {
            "url_original": "https://produto.mercadolivre.com.br/MLB-111111111-item",
            "desconto": 20,
            "comissao_percentual": 16,
            "categoria": "Eletrônicos, Áudio e Vídeo",
            "status": "sucesso",
        },
        "https://produto.mercadolivre.com.br/MLB-222222222-item": {
            "url_original": "https://produto.mercadolivre.com.br/MLB-222222222-item",
            "desconto": 40,
            "comissao_percentual": None,
            "categoria": "Calçados, Roupas e Bolsas",
            "status": "sucesso",
        },
        "https://produto.mercadolivre.com.br/MLB-333333333-item": {
            "url_original": "https://produto.mercadolivre.com.br/MLB-333333333-item",
            "desconto": 40,
            "comissao_percentual": 12,
            "categoria": "Calçados, Roupas e Bolsas",
            "status": "sucesso",
        },
    }
    engine = _FakeOffersEngine(payload_by_url=payload_by_url)

    result = asyncio.run(
        use_case.execute(
            scraper_type="ofertas",
            max_items=3,
            engine=engine,
            min_desconto_percent=30,
            min_comissao_percent=10,
        )
    )

    assert result.filtrados == 2
    assert result.novos == 1
    assert result.existentes == 0
    assert result.erros == 0
    assert offer_repository.exists_offer.await_count == 1
    assert offer_repository.upsert_offer.await_count == 1
    assert cache.set.await_count == 1


def test_offer_filter_by_category_alias():
    logger = logging.getLogger("test.offer.category")
    offer_repository = AsyncMock()
    offer_repository.ensure_offer_schema_compatibility = AsyncMock(return_value=set())
    offer_repository.exists_offer = AsyncMock(return_value=False)
    offer_repository.upsert_offer = AsyncMock(return_value=(1, True))
    coupon_repository = AsyncMock()
    cache = AsyncMock()
    cache.set = AsyncMock()

    use_case = RunScraperJobUseCase(
        logger=logger,
        offer_repository=offer_repository,
        coupon_repository=coupon_repository,
        cache=cache,
        default_min_desconto_percent=0,
        default_min_comissao_percent=0,
    )

    payload_by_url = {
        "https://produto.mercadolivre.com.br/MLB-444444444-item": {
            "url_original": "https://produto.mercadolivre.com.br/MLB-444444444-item",
            "desconto": 10,
            "comissao_percentual": 5,
            "categoria": "Calçados, Roupas e Bolsas",
            "status": "sucesso",
        },
        "https://produto.mercadolivre.com.br/MLB-555555555-item": {
            "url_original": "https://produto.mercadolivre.com.br/MLB-555555555-item",
            "desconto": 10,
            "comissao_percentual": 5,
            "categoria": "Eletrônicos, Áudio e Vídeo",
            "status": "sucesso",
        },
    }
    engine = _FakeOffersEngine(payload_by_url=payload_by_url)

    result = asyncio.run(
        use_case.execute(
            scraper_type="ofertas",
            max_items=2,
            engine=engine,
            min_desconto_percent=0,
            min_comissao_percent=0,
            category_filter="vestuario",
        )
    )

    assert result.novos == 1
    assert result.filtrados == 1


def test_offer_filter_by_multiple_categories():
    logger = logging.getLogger("test.offer.category.multi")
    offer_repository = AsyncMock()
    offer_repository.ensure_offer_schema_compatibility = AsyncMock(return_value=set())
    offer_repository.exists_offer = AsyncMock(return_value=False)
    offer_repository.upsert_offer = AsyncMock(return_value=(1, True))
    coupon_repository = AsyncMock()
    cache = AsyncMock()
    cache.set = AsyncMock()

    use_case = RunScraperJobUseCase(
        logger=logger,
        offer_repository=offer_repository,
        coupon_repository=coupon_repository,
        cache=cache,
        default_min_desconto_percent=0,
        default_min_comissao_percent=0,
    )

    payload_by_url = {
        "https://produto.mercadolivre.com.br/MLB-666666666-item": {
            "url_original": "https://produto.mercadolivre.com.br/MLB-666666666-item",
            "desconto": 10,
            "comissao_percentual": 5,
            "categoria": "Calcados, Roupas e Bolsas",
            "status": "sucesso",
        },
        "https://produto.mercadolivre.com.br/MLB-777777777-item": {
            "url_original": "https://produto.mercadolivre.com.br/MLB-777777777-item",
            "desconto": 10,
            "comissao_percentual": 5,
            "categoria": "Eletronicos, Audio e Video",
            "status": "sucesso",
        },
    }
    engine = _FakeOffersEngine(payload_by_url=payload_by_url)

    result = asyncio.run(
        use_case.execute(
            scraper_type="ofertas",
            max_items=2,
            engine=engine,
            min_desconto_percent=0,
            min_comissao_percent=0,
            category_filter=["vestuario", "eletronicos"],
        )
    )

    assert result.novos == 2
    assert result.filtrados == 0


def test_repository_upsert_offer_includes_comissao_percentual():
    fake_conn = _FakeConnection()
    fake_pool = _FakePool(fake_conn)
    fake_postgres = SimpleNamespace(require_pool=lambda: fake_pool)
    repository = PostgresOfferRepository(connection=fake_postgres)
    offer = OfferEntity.from_raw(
        {
            "url_original": "https://produto.mercadolivre.com.br/MLB-999999999-item",
            "desconto": 50,
            "comissao_percentual": 18,
            "status": "sucesso",
        }
    )

    _, inserted = asyncio.run(repository.upsert_offer(table="ml_ofertas", offer=offer, include_tempo=False))

    assert inserted is True
    assert "comissao_percentual" in fake_conn.last_sql
    assert offer.comissao_percentual in fake_conn.last_params


def test_offer_job_aborts_early_when_schema_is_incompatible():
    logger = logging.getLogger("test.offer.schema")
    offer_repository = AsyncMock()
    offer_repository.ensure_offer_schema_compatibility = AsyncMock(return_value={"comissao_percentual"})
    offer_repository.exists_offer = AsyncMock(return_value=False)
    offer_repository.upsert_offer = AsyncMock(return_value=(1, True))
    coupon_repository = AsyncMock()
    cache = AsyncMock()
    cache.set = AsyncMock()

    use_case = RunScraperJobUseCase(
        logger=logger,
        offer_repository=offer_repository,
        coupon_repository=coupon_repository,
        cache=cache,
        default_min_desconto_percent=30,
        default_min_comissao_percent=10,
    )
    engine = _FakeOffersEngine(
        payload_by_url={
            "https://produto.mercadolivre.com.br/MLB-123456789-item": {
                "url_original": "https://produto.mercadolivre.com.br/MLB-123456789-item",
                "desconto": 50,
                "comissao_percentual": 20,
                "categoria": "Eletronicos, Audio e Video",
                "status": "sucesso",
            }
        }
    )

    result = asyncio.run(
        use_case.execute(
            scraper_type="ofertas_relampago",
            max_items=1,
            engine=engine,
            min_desconto_percent=30,
            min_comissao_percent=10,
        )
    )

    assert result.novos == 0
    assert result.existentes == 0
    assert result.filtrados == 0
    assert result.erros == 1
    assert result.total_coletados == 0
    assert "alembic -c db/alembic.ini upgrade head" in result.detalhes_erros[0]
    assert offer_repository.ensure_offer_schema_compatibility.await_count == 1
    assert offer_repository.exists_offer.await_count == 0
    assert offer_repository.upsert_offer.await_count == 0
