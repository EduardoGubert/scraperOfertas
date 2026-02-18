import asyncio

from src.application.dto.scrape_result import ScrapeResultDTO
from src.application.use_cases.run_all_jobs import run_jobs_in_sequence


class _FakeUseCase:
    def __init__(self):
        self.calls: list[str] = []

    async def execute(
        self,
        scraper_type: str,
        max_items: int,
        engine,
        min_desconto_percent=None,
        min_comissao_percent=None,
        category_filter=None,
    ):
        self.calls.append(scraper_type)
        return ScrapeResultDTO(scraper_type=scraper_type)


class _FakeEngineContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _engine_factory():
    return _FakeEngineContext()


def test_run_jobs_in_sequence_default_runs_all_three():
    use_case = _FakeUseCase()

    result = asyncio.run(
        run_jobs_in_sequence(
            job_use_case=use_case,
            engine_factory=_engine_factory,
            max_items=5,
            timeout_seconds=10,
        )
    )

    assert use_case.calls == ["ofertas", "ofertas_relampago", "cupons"]
    assert result.ofertas is not None
    assert result.ofertas_relampago is not None
    assert result.cupons is not None


def test_run_jobs_in_sequence_without_cupons():
    use_case = _FakeUseCase()

    result = asyncio.run(
        run_jobs_in_sequence(
            job_use_case=use_case,
            engine_factory=_engine_factory,
            max_items=5,
            timeout_seconds=10,
            job_sequence=("ofertas", "ofertas_relampago"),
        )
    )

    assert use_case.calls == ["ofertas", "ofertas_relampago"]
    assert result.ofertas is not None
    assert result.ofertas_relampago is not None
    assert result.cupons is None
