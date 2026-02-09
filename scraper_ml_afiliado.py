"""
Entrypoint de compatibilidade do scraper.
Mantem o nome ScraperMLAfiliado usado por scripts operacionais.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.infrastructure.scraping.ml_playwright_scraper import MercadoLivrePlaywrightScraper


class _CompatCache:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data: dict[str, Any] = {"produtos": {}, "metadados": {"versao": "3.0"}}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        try:
            content = json.loads(self.file_path.read_text(encoding="utf-8"))
            if isinstance(content, dict) and "produtos" in content:
                self.data = content
        except Exception:
            self.data = {"produtos": {}, "metadados": {"versao": "3.0"}}

    def save(self) -> None:
        self.data["metadados"]["atualizado_em"] = datetime.now().isoformat()
        self.data["metadados"]["total_produtos"] = len(self.data["produtos"])
        self.file_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _hash_url(self, url: str) -> str:
        normalized = url.split("?")[0].split("#")[0].strip().lower()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:16]

    def exists(self, url: str) -> bool:
        return self._hash_url(url) in self.data["produtos"]

    def add(self, produto: dict[str, Any]) -> None:
        url = produto.get("url_original")
        if not url:
            return
        self.data["produtos"][self._hash_url(url)] = {
            "url_original": url,
            "mlb_id": produto.get("mlb_id"),
            "status": produto.get("status"),
            "cache_adicionado_em": datetime.now().isoformat(),
        }

    def clear(self) -> None:
        self.data = {"produtos": {}, "metadados": {"versao": "3.0"}}
        self.save()

    def stats(self) -> dict[str, Any]:
        return {
            "total_produtos": len(self.data["produtos"]),
            "com_link_afiliado": 0,
            "status": {},
            "arquivo": str(self.file_path),
            "tamanho_arquivo_kb": round(self.file_path.stat().st_size / 1024, 2) if self.file_path.exists() else 0,
        }


class ScraperMLAfiliado(MercadoLivrePlaywrightScraper):
    def __init__(
        self,
        headless: bool = False,
        wait_ms: int = 1500,
        max_produtos: int = 50,
        etiqueta: str = "egnofertas",
        user_data_dir: str | None = None,
        cache_file: str = "cache_produtos.json",
        usar_cache: bool = True,
    ):
        super().__init__(
            headless=headless,
            wait_ms=wait_ms,
            max_produtos=max_produtos,
            user_data_dir=user_data_dir,
        )
        self.etiqueta = etiqueta
        self.usar_cache = usar_cache
        self.cache_manager = _CompatCache(cache_file)

    async def scrape_ofertas(self, url: str | None = None, max_produtos: int | None = None) -> list[dict]:
        limit = max_produtos or self.max_produtos
        if not await self.verificar_login():
            ok = await self.fazer_login_manual()
            if not ok:
                return []

        async def seen_checker(link: str) -> bool:
            return self.cache_manager.exists(link) if self.usar_cache else False

        links = await self.collect_offer_links(
            mode="ofertas",
            max_produtos=limit,
            seen_checker=seen_checker,
            start_url=url,
        )
        items: list[dict] = []
        for link in links:
            produto = await self.extract_offer_product(link, include_tempo=False)
            if self.usar_cache:
                self.cache_manager.add(produto)
            items.append(produto)
            await asyncio.sleep(0.1)

        if self.usar_cache:
            self.cache_manager.save()
        return items

    async def scrape_ofertas_relampago(self, max_produtos: int | None = None) -> list[dict]:
        limit = max_produtos or self.max_produtos
        if not await self.verificar_login():
            ok = await self.fazer_login_manual()
            if not ok:
                return []

        async def seen_checker(link: str) -> bool:
            return self.cache_manager.exists(link) if self.usar_cache else False

        links = await self.collect_offer_links(
            mode="ofertas_relampago",
            max_produtos=limit,
            seen_checker=seen_checker,
        )
        items: list[dict] = []
        for link in links:
            produto = await self.extract_offer_product(link, include_tempo=True)
            if self.usar_cache:
                self.cache_manager.add(produto)
            items.append(produto)
            await asyncio.sleep(0.1)

        if self.usar_cache:
            self.cache_manager.save()
        return items

    def limpar_cache(self) -> None:
        self.cache_manager.clear()

    def estatisticas_cache(self) -> dict[str, Any]:
        return self.cache_manager.stats()


async def main():
    import sys

    limpar_cache = "--limpar-cache" in sys.argv

    async with ScraperMLAfiliado(
        headless=False,
        wait_ms=1500,
        max_produtos=50,
        etiqueta="egnofertas",
        usar_cache=True,
        cache_file="cache_produtos.json",
    ) as scraper:
        if limpar_cache:
            scraper.limpar_cache()

        produtos = await scraper.scrape_ofertas()
        if produtos:
            arquivo = await scraper.salvar_resultados(produtos)
            print(f"Resultados salvos em: {arquivo}")
        else:
            print("Nenhum produto novo encontrado")


if __name__ == "__main__":
    asyncio.run(main())
