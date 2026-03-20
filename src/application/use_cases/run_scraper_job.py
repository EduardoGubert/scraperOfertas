from __future__ import annotations

import logging
from uuid import uuid4

from src.application.dto.scrape_result import ScrapeResultDTO
from src.application.services.deduplication_service import CouponDeduplicationService, OfferDeduplicationService
from src.domain.entities.coupons import CouponEntity
from src.domain.entities.offers import OfferEntity
from src.domain.value_objects.categories import category_matches, resolve_category_filters
from src.infrastructure.scraping.parsers import parse_coupon_card
from src.infrastructure.scraping.scrapers import CuponsScraper, OfertasRelampagoScraper, OfertasScraper


TABLE_BY_SCRAPER = {
    "ofertas": "ml_ofertas",
    "ofertas_relampago": "ml_ofertas_relampago",
}


class OfferSchemaMismatchError(RuntimeError):
    def __init__(self, table: str, missing_columns: set[str]):
        self.table = table
        self.missing_columns = set(missing_columns)
        missing_label = ", ".join(sorted(self.missing_columns))
        super().__init__(
            f"Schema incompativel para tabela {table}: colunas ausentes [{missing_label}]. "
            "Execute: alembic -c db/alembic.ini upgrade head"
        )


class RunScraperJobUseCase:
    def __init__(
        self,
        logger: logging.Logger,
        offer_repository,
        coupon_repository,
        cache,
        default_min_desconto_percent: int = 30,
        default_min_comissao_percent: int = 10,
        default_category_filter: str | None = None,
    ):
        self.logger = logger
        self.offer_repository = offer_repository
        self.coupon_repository = coupon_repository
        self.cache = cache
        self.default_min_desconto_percent = max(0, int(default_min_desconto_percent))
        self.default_min_comissao_percent = max(0, int(default_min_comissao_percent))
        self.default_category_filters = resolve_category_filters(default_category_filter)

    async def execute(
        self,
        scraper_type: str,
        max_items: int,
        engine,
        start_url: str | None = None,
        min_desconto_percent: int | None = None,
        min_comissao_percent: int | None = None,
        category_filter: str | list[str] | None = None,
    ) -> ScrapeResultDTO:
        job_id = str(uuid4())[:8]
        result = ScrapeResultDTO(scraper_type=scraper_type)
        aborted_reason: str | None = None
        effective_min_desconto = (
            self.default_min_desconto_percent if min_desconto_percent is None else max(0, int(min_desconto_percent))
        )
        effective_min_comissao = (
            self.default_min_comissao_percent if min_comissao_percent is None else max(0, int(min_comissao_percent))
        )
        effective_category_filters = resolve_category_filters(
            self.default_category_filters if category_filter is None else category_filter
        )
        categories_label = ", ".join(effective_category_filters) if effective_category_filters else "todas"
        self.logger.info(
            "Iniciando job de scraping | "
            f"job_id={job_id} scraper_type={scraper_type} max_items={max_items} "
            f"min_desconto={effective_min_desconto} min_comissao={effective_min_comissao} "
            f"category_filter={categories_label}"
        )

        if scraper_type in {"ofertas", "ofertas_relampago"}:
            try:
                result = await self._execute_offers_job(
                    scraper_type=scraper_type,
                    max_items=max_items,
                    engine=engine,
                    job_id=job_id,
                    start_url=start_url,
                    min_desconto_percent=effective_min_desconto,
                    min_comissao_percent=effective_min_comissao,
                    category_filter=effective_category_filters,
                )
            except OfferSchemaMismatchError as exc:
                result.erros = 1
                aborted_reason = str(exc)
                result.detalhes_erros.append(aborted_reason)
                self.logger.error(
                    "Job abortado por incompatibilidade de schema | "
                    f"job_id={job_id} scraper_type={scraper_type} tabela={exc.table} "
                    f"colunas_ausentes={','.join(sorted(exc.missing_columns))} "
                    "acao='alembic -c db/alembic.ini upgrade head'"
                )
        elif scraper_type == "cupons":
            if min_desconto_percent is not None or min_comissao_percent is not None or category_filter is not None:
                self.logger.info(
                    "Filtros de desconto/comissao ignorados para cupons | "
                    f"job_id={job_id} min_desconto={effective_min_desconto} min_comissao={effective_min_comissao} "
                    f"categoria={categories_label}"
                )
            result = await self._execute_coupons_job(
                max_items=max_items,
                engine=engine,
                job_id=job_id,
            )
        else:
            raise ValueError(f"scraper_type invalido: {scraper_type}")

        self.logger.info(
            f"Job finalizado | job_id={job_id} scraper_type={scraper_type} "
            f"novos={result.novos} existentes={result.existentes} filtrados={result.filtrados} erros={result.erros} "
            f"aborted={'sim' if aborted_reason else 'nao'}"
        )
        if aborted_reason:
            self.logger.info(
                "Causa raiz do aborto do job | "
                f"job_id={job_id} scraper_type={scraper_type} motivo={aborted_reason}"
            )
        return result

    async def _execute_offers_job(
        self,
        scraper_type: str,
        max_items: int,
        engine,
        job_id: str,
        start_url: str | None = None,
        min_desconto_percent: int = 0,
        min_comissao_percent: int = 0,
        category_filter: list[str] | None = None,
    ) -> ScrapeResultDTO:
        categories_label = ", ".join(category_filter) if category_filter else "todas"
        table_name = TABLE_BY_SCRAPER[scraper_type]
        include_tempo = scraper_type == "ofertas_relampago"
        required_columns = {"comissao_percentual"}
        if include_tempo:
            required_columns.add("tempo_para_acabar")

        missing_columns = await self.offer_repository.ensure_offer_schema_compatibility(
            table=table_name,
            required_columns=required_columns,
        )
        if missing_columns:
            raise OfferSchemaMismatchError(table=table_name, missing_columns=missing_columns)

        result = ScrapeResultDTO(scraper_type=scraper_type)
        aprovados_log: list[dict[str, str | int]] = []
        filtrados_log: list[dict[str, str | int]] = []
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
        self.logger.info(
            "Links coletados | "
            f"job_id={job_id} scraper_type={scraper_type} total_links={len(links)} "
            f"min_desconto={min_desconto_percent} min_comissao={min_comissao_percent} "
            f"categoria={categories_label}"
        )

        for idx, link in enumerate(links, start=1):
            try:
                raw = await scraper.extract_product(link)
                offer = OfferEntity.from_raw(raw, include_tempo=include_tempo)
                if not offer.minimal_required():
                    result.erros += 1
                    result.detalhes_erros.append(f"Item sem campos minimos: {link}")
                    continue

                desconto_efetivo = offer.desconto or 0
                comissao_extraida = offer.comissao_percentual
                comissao_efetiva = comissao_extraida if comissao_extraida is not None else 0
                comissao_auditoria: int | str = comissao_extraida if comissao_extraida is not None else "indisponivel"
                categoria_produto = offer.categoria
                motivos_filtro: list[str] = []
                if desconto_efetivo < min_desconto_percent:
                    motivos_filtro.append(f"desconto={desconto_efetivo}/{min_desconto_percent}")
                if comissao_extraida is None:
                    motivos_filtro.append(f"comissao=indisponivel/{min_comissao_percent}")
                elif comissao_efetiva < min_comissao_percent:
                    motivos_filtro.append(f"comissao={comissao_efetiva}/{min_comissao_percent}")
                if category_filter and not category_matches(category_filter, categoria_produto):
                    motivos_filtro.append(
                        f"categoria={categoria_produto or 'sem_categoria'}~{categories_label}"
                    )
                link_afiliado = offer.url_afiliado or offer.url_curta or "sem_link"

                if motivos_filtro:
                    result.filtrados += 1
                    filtrados_log.append(
                        {
                            "index": idx,
                            "mlb_id": offer.mlb_id or "sem_mlb_id",
                            "dedupe": offer.chave_dedupe,
                            "categoria": categoria_produto or "sem_categoria",
                            "desconto": desconto_efetivo,
                            "comissao": comissao_auditoria,
                            "motivos": " ; ".join(motivos_filtro),
                            "link": link_afiliado,
                        }
                    )
                    self.logger.info(
                        "Produto descartado por filtro | "
                        f"job_id={job_id} scraper_type={scraper_type} index={idx} "
                        f"dedupe={offer.chave_dedupe} motivos={' ; '.join(motivos_filtro)}"
                    )
                    continue

                aprovados_log.append(
                    {
                        "index": idx,
                        "mlb_id": offer.mlb_id or "sem_mlb_id",
                        "dedupe": offer.chave_dedupe,
                        "categoria": categoria_produto or "sem_categoria",
                        "desconto": desconto_efetivo,
                        "comissao": comissao_auditoria,
                        "status": offer.status,
                        "link": link_afiliado,
                    }
                )
                self.logger.info(
                    "Produto aprovado em filtro | "
                    f"job_id={job_id} scraper_type={scraper_type} index={idx} "
                    f"dedupe={offer.chave_dedupe} passou_filtro=True "
                    f"desconto={desconto_efetivo} comissao={comissao_auditoria} "
                    f"categoria={categoria_produto or 'sem_categoria'}"
                )
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

        self._log_auditoria_resumo(
            job_id=job_id,
            scraper_type=scraper_type,
            total_coletados=result.total_coletados,
            aprovados=aprovados_log,
            filtrados=filtrados_log,
        )
        return result

    async def _execute_coupons_job(self, max_items: int, engine, job_id: str) -> ScrapeResultDTO:
        result = ScrapeResultDTO(scraper_type="cupons")
        aprovados_log: list[dict[str, str | int]] = []
        filtrados_log: list[dict[str, str | int]] = []
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
                    aprovados_log.append(
                        {
                            "index": idx,
                            "dedupe": coupon.chave_dedupe,
                            "nome": coupon.nome or "sem_nome",
                            "desconto": coupon.desconto_percentual if coupon.desconto_percentual is not None else "n/a",
                            "comissao": "n/a",
                            "status": "existente",
                            "categoria": "n/a",
                            "link": "sem_link",
                            "url_origem": coupon.url_origem or "sem_url_origem",
                        }
                    )
                    continue

                _, inserted = await self.coupon_repository.upsert_coupon(coupon)
                if inserted:
                    result.novos += 1
                else:
                    result.existentes += 1
                await dedupe.mark_seen(coupon.chave_dedupe)
                result.itens.append(parsed)
                aprovados_log.append(
                    {
                        "index": idx,
                        "dedupe": coupon.chave_dedupe,
                        "nome": coupon.nome or "sem_nome",
                        "desconto": coupon.desconto_percentual if coupon.desconto_percentual is not None else "n/a",
                        "comissao": "n/a",
                        "status": "novo" if inserted else "existente",
                        "categoria": "n/a",
                        "link": "sem_link",
                        "url_origem": coupon.url_origem or "sem_url_origem",
                    }
                )
                self.logger.info(
                    f"Cupom processado | job_id={job_id} index={idx} dedupe={coupon.chave_dedupe}"
                )
            except Exception as exc:
                result.erros += 1
                result.detalhes_erros.append(str(exc))
                self.logger.error(f"Erro ao processar cupom | job_id={job_id} index={idx} erro={exc}")

        self._log_auditoria_resumo(
            job_id=job_id,
            scraper_type="cupons",
            total_coletados=result.total_coletados,
            aprovados=aprovados_log,
            filtrados=filtrados_log,
        )
        return result

    def _log_auditoria_resumo(
        self,
        job_id: str,
        scraper_type: str,
        total_coletados: int,
        aprovados: list[dict[str, str | int]],
        filtrados: list[dict[str, str | int]],
    ) -> None:
        self.logger.info(
            "Relatorio auditoria | "
            f"job_id={job_id} scraper_type={scraper_type} total_coletados={total_coletados} "
            f"aprovados={len(aprovados)} filtrados={len(filtrados)}"
        )
        self.logger.info(
            "Relatorio auditoria | "
            f"job_id={job_id} scraper_type={scraper_type} secao=APROVADOS total={len(aprovados)}"
        )
        for item in aprovados:
            self.logger.info(
                "Relatorio auditoria | "
                "Aprovado | "
                f"job_id={job_id} scraper_type={scraper_type} "
                f"index={item.get('index')} "
                f"mlb_id={item.get('mlb_id', 'n/a')} "
                f"nome={item.get('nome', 'n/a')} "
                f"dedupe={item.get('dedupe', 'n/a')} "
                f"categoria={item.get('categoria', 'n/a')} "
                f"desconto={item.get('desconto', 'n/a')} "
                f"comissao={item.get('comissao', 'n/a')} "
                f"status={item.get('status', 'n/a')} "
                f"link={item.get('link', 'sem_link')} "
                f"url_origem={item.get('url_origem', 'n/a')}"
            )
        self.logger.info(
            "Relatorio auditoria | "
            f"job_id={job_id} scraper_type={scraper_type} secao=FILTRADOS total={len(filtrados)}"
        )
        for item in filtrados:
            self.logger.info(
                "Relatorio auditoria | "
                "Filtrado | "
                f"job_id={job_id} scraper_type={scraper_type} "
                f"index={item.get('index')} "
                f"mlb_id={item.get('mlb_id', 'n/a')} "
                f"nome={item.get('nome', 'n/a')} "
                f"dedupe={item.get('dedupe', 'n/a')} "
                f"categoria={item.get('categoria', 'n/a')} "
                f"desconto={item.get('desconto', 'n/a')} "
                f"comissao={item.get('comissao', 'n/a')} "
                f"motivos={item.get('motivos', 'n/a')} "
                f"link={item.get('link', 'sem_link')} "
                f"url_origem={item.get('url_origem', 'n/a')}"
            )
