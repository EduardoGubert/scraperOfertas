from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.application.dto.scrape_result import ScrapeResultDTO


@dataclass
class AllJobsResult:
    ofertas: ScrapeResultDTO
    ofertas_relampago: ScrapeResultDTO
    cupons: ScrapeResultDTO


async def run_jobs_in_sequence(job_use_case, engine_factory, max_items: int, timeout_seconds: int) -> AllJobsResult:
    async def run_single(scraper_type: str) -> ScrapeResultDTO:
        async with engine_factory() as engine:
            return await asyncio.wait_for(
                job_use_case.execute(scraper_type=scraper_type, max_items=max_items, engine=engine),
                timeout=timeout_seconds,
            )

    ofertas = await run_single("ofertas")
    relampago = await run_single("ofertas_relampago")
    cupons = await run_single("cupons")
    return AllJobsResult(ofertas=ofertas, ofertas_relampago=relampago, cupons=cupons)
