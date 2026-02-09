from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timedelta

from src.application.use_cases.run_all_jobs import run_jobs_in_sequence
from src.bootstrap import build_container
from src.infrastructure.config.settings import get_settings
from src.infrastructure.logging.logger import setup_logging


class ScraperScheduler:
    def __init__(
        self,
        intervalo_minutos: int,
        max_produtos: int,
        job_timeout_seconds: int,
        headless: bool = True,
    ):
        self.intervalo_minutos = intervalo_minutos
        self.max_produtos = max_produtos
        self.job_timeout_seconds = job_timeout_seconds
        self.headless = headless
        self.rodando = False
        self.proximo_run: datetime | None = None
        self.logger = setup_logging(log_name="scheduler", filename_prefix="scheduler")

    async def _run_single_job(self, scraper_type: str) -> dict:
        async with build_container() as container:
            async with container.engine_factory(headless=self.headless, max_produtos=self.max_produtos) as engine:
                result = await asyncio.wait_for(
                    container.job_use_case.execute(scraper_type=scraper_type, max_items=self.max_produtos, engine=engine),
                    timeout=self.job_timeout_seconds,
                )
                return result.__dict__

    async def executar_todos_sequencial(self) -> dict:
        self.logger.info(
            f"Iniciando execucao sequencial | max_produtos={self.max_produtos} timeout_s={self.job_timeout_seconds}"
        )
        started_at = datetime.now()
        async with build_container() as container:
            results = await run_jobs_in_sequence(
                job_use_case=container.job_use_case,
                engine_factory=lambda: container.engine_factory(headless=self.headless, max_produtos=self.max_produtos),
                max_items=self.max_produtos,
                timeout_seconds=self.job_timeout_seconds,
            )
        finished_at = datetime.now()
        payload = {
            "iniciado_em": started_at.isoformat(),
            "finalizado_em": finished_at.isoformat(),
            "duracao_segundos": int((finished_at - started_at).total_seconds()),
            "ofertas": results.ofertas.__dict__,
            "ofertas_relampago": results.ofertas_relampago.__dict__,
            "cupons": results.cupons.__dict__,
        }
        self.logger.info("Execucao sequencial concluida com sucesso")
        return payload

    def calcular_proximo_run(self) -> datetime:
        self.proximo_run = datetime.now() + timedelta(minutes=self.intervalo_minutos)
        return self.proximo_run

    def iniciar_scheduler(self) -> None:
        self.logger.info("Scheduler iniciado")
        self.logger.info(
            f"Configuracao | intervalo_minutos={self.intervalo_minutos} "
            f"max_produtos={self.max_produtos} timeout_s={self.job_timeout_seconds}"
        )
        self.rodando = True

        self.logger.info("Executando rodada inicial")
        self.job_wrapper()
        self.calcular_proximo_run()
        self.logger.info(f"Proxima execucao: {self.proximo_run}")

        try:
            while self.rodando:
                now = datetime.now()
                if self.proximo_run and now >= self.proximo_run:
                    self.logger.info(f"Executando rodada agendada | now={now.isoformat()}")
                    self.job_wrapper()
                    self.calcular_proximo_run()
                    self.logger.info(f"Proxima execucao: {self.proximo_run}")
                time.sleep(30)
        except KeyboardInterrupt:
            self.logger.info("Scheduler interrompido pelo usuario")
        finally:
            self.rodando = False

    def job_wrapper(self) -> None:
        try:
            asyncio.run(self.executar_todos_sequencial())
        except asyncio.TimeoutError:
            self.logger.error("Timeout na execucao de um job")
        except Exception as exc:
            self.logger.error(f"Erro critico no scheduler: {exc}")


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Scheduler para scraperOfertas")
    parser.add_argument("--intervalo", type=int, default=settings.scheduler_interval_minutes)
    parser.add_argument("--produtos", type=int, default=settings.scheduler_max_produtos)
    parser.add_argument(
        "--job-timeout-seconds",
        type=int,
        default=settings.scheduler_job_timeout_seconds,
        help="Timeout por job em segundos",
    )
    parser.add_argument("--agora", action="store_true", help="Executa uma rodada completa e sai")
    args = parser.parse_args()

    scheduler = ScraperScheduler(
        intervalo_minutos=args.intervalo,
        max_produtos=args.produtos,
        job_timeout_seconds=args.job_timeout_seconds,
        headless=True,
    )
    if args.agora:
        scheduler.job_wrapper()
    else:
        scheduler.iniciar_scheduler()


if __name__ == "__main__":
    main()
