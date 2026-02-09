from __future__ import annotations

import logging
from uuid import uuid4

from src.application.dto.scrape_result import ScrapeResultDTO
from src.application.services.deduplication_service import CouponDeduplicationService, OfferDeduplicationService
from src.domain.entities.coupons import CouponEntity
from src.domain.entities.offers import OfferEntity
from src.infrastructure.scraping.parsers import parse_coupon_card
from src.infrastructure.scraping.scrapers import CuponsScraper, OfertasRelampagoScraper, OfertasScraper


TABLE_BY_SCRAPER = {
    "ofertas": "ml_ofertas",
    "ofertas_relampago": "ml_ofertas_relampago",
}


class RunScraperJobUseCase:
    def __init__(
        self,
        logger: logging.Logger,
        offer_repository,
        coupon_repository,
        cache,
    ):
        self.logger = logger
        self.offer_repository = offer_repository
        self.coupon_repository = coupon_repository
        self.cache = cache

    async def execute(self, scraper_type: str, max_items: int, engine, start_url: str | None = None) -> ScrapeResultDTO:
        job_id = str(uuid4())[:8]
        result = ScrapeResultDTO(scraper_type=scraper_type)
        self.logger.info(
            f"Iniciando job de scraping | job_id={job_id} scraper_type={scraper_type} max_items={max_items}"
        )

        if scraper_type in {"ofertas", "ofertas_relampago"}:
            result = await self._execute_offers_job(
                scraper_type=scraper_type,
                max_items=max_items,
                engine=engine,
                job_id=job_id,
                start_url=start_url,
            )
        elif scraper_type == "cupons":
            result = await self._execute_coupons_job(
                max_items=max_items,
                engine=engine,
                job_id=job_id,
            )
        else:
            raise ValueError(f"scraper_type invalido: {scraper_type}")

        self.logger.info(
            f"Job finalizado | job_id={job_id} scraper_type={scraper_type} "
            f"novos={result.novos} existentes={result.existentes} erros={result.erros}"
        )
        return result

    async def _execute_offers_job(
        self,
        scraper_type: str,
        max_items: int,
        engine,
        job_id: str,
        start_url: str | None = None,
    ) -> ScrapeResultDTO:
        table_name = TABLE_BY_SCRAPER[scraper_type]
        include_tempo = scraper_type == "ofertas_relampago"

        result = ScrapeResultDTO(scraper_type=scraper_type)
        dedupe = OfferDeduplicationService(
            repository=self.offer_repository,
            cache=self.cache,
            scraper_type=scraper_type,
            table_name=table_name,
        )

        scraper = OfertasRelampagoScraper(engine) if include_tempo else OfertasScraper(engine)
        links = await scraper.collect_links(
            max_produtos=max_items,
            seen_checker=dedupe.is_seen_by_url,
            start_url=start_url,
        )
        result.total_coletados = len(links)
        self.logger.info(f"Links coletados | job_id={job_id} scraper_type={scraper_type} total_links={len(links)}")

        for idx, link in enumerate(links, start=1):
            try:
                raw = await scraper.extract_product(link)
                offer = OfferEntity.from_raw(raw, include_tempo=include_tempo)
                if not offer.minimal_required():
                    result.erros += 1
                    result.detalhes_erros.append(f"Item sem campos minimos: {link}")
                    continue

                exists_in_db = await self.offer_repository.exists_offer(table_name, offer.chave_dedupe, offer.mlb_id)
                if exists_in_db:
                    result.existentes += 1
                    await dedupe.mark_seen(offer.chave_dedupe)
                    continue

                _, inserted = await self.offer_repository.upsert_offer(
                    table=table_name,
                    offer=offer,
                    include_tempo=include_tempo,
                )
                if inserted:
                    result.novos += 1
                else:
                    result.existentes += 1
                await dedupe.mark_seen(offer.chave_dedupe)
                result.itens.append(raw)
                self.logger.info(
                    f"Produto processado | job_id={job_id} scraper_type={scraper_type} "
                    f"index={idx} status={raw.get('status')} dedupe={offer.chave_dedupe}"
                )
            except Exception as exc:
                result.erros += 1
                result.detalhes_erros.append(str(exc))
                self.logger.error(
                    f"Erro ao processar produto | job_id={job_id} scraper_type={scraper_type} index={idx} erro={exc}"
                )

        return result

    async def _execute_coupons_job(self, max_items: int, engine, job_id: str) -> ScrapeResultDTO:
        result = ScrapeResultDTO(scraper_type="cupons")
        dedupe = CouponDeduplicationService(repository=self.coupon_repository, cache=self.cache)
        scraper = CuponsScraper(engine)

        raw_coupons = await scraper.scrape(max_cupons=max_items)
        result.total_coletados = len(raw_coupons)
        self.logger.info(f"Cupons coletados | job_id={job_id} total_cupons={len(raw_coupons)}")

        for idx, raw in enumerate(raw_coupons, start=1):
            try:
                parsed = parse_coupon_card(raw)
                coupon = CouponEntity.from_raw(parsed, source_url=raw.get("url_origem") or "")
                if not coupon.minimal_required():
                    result.erros += 1
                    result.detalhes_erros.append(f"Cupom sem campos minimos na posicao {idx}")
                    continue

                if await dedupe.is_seen(coupon.chave_dedupe):
                    result.existentes += 1
                    continue

                _, inserted = await self.coupon_repository.upsert_coupon(coupon)
                if inserted:
                    result.novos += 1
                else:
                    result.existentes += 1
                await dedupe.mark_seen(coupon.chave_dedupe)
                result.itens.append(parsed)
                self.logger.info(
                    f"Cupom processado | job_id={job_id} index={idx} dedupe={coupon.chave_dedupe}"
                )
            except Exception as exc:
                result.erros += 1
                result.detalhes_erros.append(str(exc))
                self.logger.error(f"Erro ao processar cupom | job_id={job_id} index={idx} erro={exc}")

        return result
