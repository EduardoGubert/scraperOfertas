#!/usr/bin/env python3
"""Pipeline legado de compatibilidade.
Executa o job de ofertas usando a nova arquitetura.
"""

import argparse
import asyncio

from src.bootstrap import build_container
from src.infrastructure.config.settings import get_settings


async def run_pipeline(max_produtos: int, headless: bool) -> dict:
    settings = get_settings()
    async with build_container(settings) as container:
        async with container.engine_factory(headless=headless, max_produtos=max_produtos) as engine:
            result = await container.job_use_case.execute(
                scraper_type="ofertas",
                max_items=max_produtos,
                engine=engine,
            )
            return result.__dict__


def obter_max_produtos() -> int:
    parser = argparse.ArgumentParser(description="Pipeline de Scraping ML")
    parser.add_argument("--max-produtos", type=int, default=None)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if args.max_produtos:
        return args.max_produtos

    while True:
        resposta = input("Quantos produtos deseja processar? [padrao: 20]: ").strip()
        if not resposta:
            return 20
        try:
            parsed = int(resposta)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
        print("Digite um numero valido maior que zero.")


async def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--headless", action="store_true")
    args, _ = parser.parse_known_args()

    max_produtos = obter_max_produtos()
    headless = args.headless if args.headless else settings.scraper_headless

    stats = await run_pipeline(max_produtos=max_produtos, headless=headless)
    print(
        "Pipeline concluido | "
        f"novos={stats['novos']} existentes={stats['existentes']} erros={stats['erros']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
