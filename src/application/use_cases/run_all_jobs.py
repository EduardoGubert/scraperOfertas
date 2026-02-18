from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Sequence

from src.application.dto.scrape_result import ScrapeResultDTO

VALID_SCRAPER_TYPES = ("ofertas", "ofertas_relampago", "cupons")


@dataclass
class AllJobsResult:
    ofertas: ScrapeResultDTO | None = None
    ofertas_relampago: ScrapeResultDTO | None = None
    cupons: ScrapeResultDTO | None = None


async def run_jobs_in_sequence(
    job_use_case,
    engine_factory,
    max_items: int,
    timeout_seconds: int,
    job_sequence: Sequence[str] | None = None,
    min_desconto_percent: int | None = None,
    min_comissao_percent: int | None = None,
    category_filter: str | list[str] | None = None,
) -> AllJobsResult:
    async def run_single(scraper_type: str) -> ScrapeResultDTO:
        async with engine_factory() as engine:
            return await asyncio.wait_for(
                job_use_case.execute(
                    scraper_type=scraper_type,
                    max_items=max_items,
                    engine=engine,
                    min_desconto_percent=min_desconto_percent,
                    min_comissao_percent=min_comissao_percent,
                    category_filter=category_filter,
                ),
                timeout=timeout_seconds,
            )

    sequence = tuple(job_sequence) if job_sequence is not None else VALID_SCRAPER_TYPES
    invalid_types = [scraper_type for scraper_type in sequence if scraper_type not in VALID_SCRAPER_TYPES]
    if invalid_types:
        raise ValueError(f"scraper_type(s) invalido(s): {', '.join(invalid_types)}")

    results_by_type: dict[str, ScrapeResultDTO] = {}
    for scraper_type in sequence:
        results_by_type[scraper_type] = await run_single(scraper_type)

    return AllJobsResult(
        ofertas=results_by_type.get("ofertas"),
        ofertas_relampago=results_by_type.get("ofertas_relampago"),
        cupons=results_by_type.get("cupons"),
    )
