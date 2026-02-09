from __future__ import annotations

import asyncio
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page, async_playwright

from src.domain.interfaces.scrapers import SeenChecker
from src.infrastructure.scraping.selectors.coupons import (
    CUPONS_CARDS_CONTAINER_XPATH,
    CUPONS_FILTER_ACABAM_HOJE_XPATH,
    CUPONS_URL,
)
from src.infrastructure.scraping.selectors.offers import (
    OFFERS_RELAMPAGO_URL,
    OFFERS_URL,
    PAGINATION_CONTAINER_XPATH,
    RELAMPAGO_FILTER_XPATH,
    RELAMPAGO_TEMPO_XPATH,
    SHARE_BUTTON_XPATH,
    SHARE_MODAL_INPUT_XPATH,
)


class MercadoLivrePlaywrightScraper:
    USER_DATA_DIR = "./ml_browser_data"

    def __init__(
        self,
        headless: bool = True,
        wait_ms: int = 1500,
        max_produtos: int = 30,
        user_data_dir: str | None = None,
    ):
        self.headless = headless
        self.wait_ms = wait_ms
        self.max_produtos = max_produtos
        self.user_data_dir = user_data_dir or self.USER_DATA_DIR

        self.playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> "MercadoLivrePlaywrightScraper":
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._close_browser()

    async def _init_browser(self) -> None:
        self.playwright = await async_playwright().start()
        is_docker = os.path.exists("/app")
        browser_channel = None if is_docker else "chrome"

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            channel=browser_channel,
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            geolocation={"latitude": -23.5505, "longitude": -46.6333},
            permissions=["geolocation"],
            color_scheme="light",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-features=IsolateOrigins,site-per-process",
                "--enable-features=NetworkService,NetworkServiceInProcess",
            ],
            ignore_default_args=["--enable-automation"],
        )

        self.page = await self.context.new_page()
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = window.chrome || { runtime: {} };
            """
        )

    async def _close_browser(self) -> None:
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        self.context = None
        self.playwright = None
        self.page = None

    async def _human_delay(self, min_ms: int = 400, max_ms: int = 1200) -> None:
        await asyncio.sleep(random.randint(min_ms, max_ms) / 1000)

    async def _scroll_suave(self, vezes: int = 4) -> None:
        assert self.page
        for _ in range(vezes):
            await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await self._human_delay(250, 650)
        await self.page.evaluate("window.scrollTo(0, 0)")
        await self._human_delay(200, 400)

    async def verificar_login(self) -> bool:
        assert self.page
        try:
            await self.page.goto(OFFERS_URL, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1000, 1600)

            afiliado_element = await self.page.query_selector(
                "[class*='affiliate'], [class*='nav-affiliate'], :text('Afiliados'), :text('GANHOS')"
            )
            if afiliado_element:
                return True

            user_element = await self.page.query_selector(
                "[class*='user-name'], [class*='nav-header-user'], :text('Eduardo')"
            )
            return bool(user_element)
        except Exception:
            return False

    async def fazer_login_manual(self) -> bool:
        assert self.page
        await self.page.goto("https://www.mercadolivre.com.br", wait_until="domcontentloaded")
        await self._human_delay(800, 1500)
        try:
            login_btn = await self.page.query_selector("a[href*='login'], :text('Entre')")
            if login_btn:
                await login_btn.click()
        except Exception:
            pass
        input("Pressione ENTER apos concluir o login manual no navegador...")
        return await self.verificar_login()

    async def _click_relampago_filter(self) -> None:
        assert self.page
        await self._human_delay(1200, 2000)
        clicked = await self.page.evaluate(
            f"""
            () => {{
                const xpath = "{RELAMPAGO_FILTER_XPATH}";
                const node = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (node) {{
                    node.click();
                    return true;
                }}
                return false;
            }}
            """
        )
        if clicked:
            await self._human_delay(2200, 3200)

    async def _extract_links_from_current_page(self) -> list[str]:
        assert self.page
        links = await self.page.evaluate(
            """
            () => {
                const set = new Set();
                const anchors = document.querySelectorAll('a[href*="/p/MLB"], a[href*="produto.mercadolivre"]');
                anchors.forEach((a) => {
                    const href = a.href || '';
                    if (!href) return;
                    const normalized = href.split('#')[0].split('?')[0];
                    if (normalized.includes('/p/MLB') || normalized.includes('produto.mercadolivre')) {
                        set.add(normalized);
                    }
                });
                return Array.from(set);
            }
            """
        )
        return links or []

    async def _go_to_next_offers_page(self) -> bool:
        assert self.page
        result = await self.page.evaluate(
            f"""
            () => {{
                const xpath = "{PAGINATION_CONTAINER_XPATH}";
                const container = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!container) return {{ moved: false, reason: "pagination_container_not_found" }};

                const items = Array.from(container.querySelectorAll("li"));
                if (!items.length) return {{ moved: false, reason: "pagination_items_not_found" }};

                let currentIndex = -1;
                for (let i = 0; i < items.length; i++) {{
                    const li = items[i];
                    const cls = (li.className || "").toLowerCase();
                    const anchor = li.querySelector("a,button");
                    const ariaCurrent = li.getAttribute("aria-current") || anchor?.getAttribute("aria-current");
                    if (ariaCurrent === "page" || cls.includes("selected") || cls.includes("current")) {{
                        currentIndex = i;
                        break;
                    }}
                }}

                let nextTarget = null;
                if (currentIndex >= 0 && currentIndex + 1 < items.length) {{
                    nextTarget = items[currentIndex + 1].querySelector("a,button");
                }}

                if (!nextTarget) {{
                    for (const li of items) {{
                        const candidate = li.querySelector("a,button");
                        const text = (candidate?.textContent || "").toLowerCase();
                        if (text.includes("próxima") || text.includes("proxima") || text.includes("seguinte") || text.includes("next")) {{
                            nextTarget = candidate;
                            break;
                        }}
                    }}
                }}

                if (!nextTarget) return {{ moved: false, reason: "next_button_not_found" }};

                const disabled = nextTarget.hasAttribute("disabled")
                    || nextTarget.getAttribute("aria-disabled") === "true"
                    || (nextTarget.className || "").toLowerCase().includes("disabled");
                if (disabled) return {{ moved: false, reason: "next_button_disabled" }};

                nextTarget.click();
                return {{ moved: true, reason: "clicked_next_page" }};
            }}
            """
        )
        if result and result.get("moved"):
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            await self._human_delay(1000, 1500)
            return True
        return False

    async def collect_offer_links(
        self,
        mode: str,
        max_produtos: int,
        seen_checker: SeenChecker | None = None,
        start_url: str | None = None,
    ) -> list[str]:
        assert self.page
        base_url = start_url or (OFFERS_RELAMPAGO_URL if mode == "ofertas_relampago" else OFFERS_URL)
        await self.page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
        await self._human_delay(1200, 1800)

        if mode == "ofertas_relampago":
            await self._click_relampago_filter()

        collected: list[str] = []
        seen_local: set[str] = set()
        max_pages = 20

        for _ in range(max_pages):
            await self._scroll_suave(vezes=5)
            page_links = await self._extract_links_from_current_page()
            if not page_links:
                break

            novos_na_pagina = 0
            for link in page_links:
                if link in seen_local:
                    continue
                seen_local.add(link)

                already_seen = False
                if seen_checker is not None:
                    already_seen = await seen_checker(link)
                if already_seen:
                    continue

                collected.append(link)
                novos_na_pagina += 1
                if len(collected) >= max_produtos:
                    return collected[:max_produtos]

            # Regra obrigatoria: se todos da pagina ja vistos, tenta proxima pagina.
            # Para completar max_produtos, tambem avanca de pagina quando ainda ha capacidade.
            if novos_na_pagina == 0 or len(collected) < max_produtos:
                moved = await self._go_to_next_offers_page()
                if not moved:
                    break
            else:
                break

        return collected[:max_produtos]

    def _parse_preco(self, valor: str | None) -> float | None:
        if not valor:
            return None
        cleaned = valor.replace(".", "").replace(",", ".").strip()
        cleaned = re.sub(r"[^\d.]", "", cleaned)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_desconto(self, valor: str | None) -> int | None:
        if not valor:
            return None
        match = re.search(r"(\d+)\s*%", valor)
        if not match:
            return None
        return int(match.group(1))

    async def _extract_tempo_para_acabar(self) -> str | None:
        assert self.page
        text = await self.page.evaluate(
            f"""
            () => {{
                const xpath = "{RELAMPAGO_TEMPO_XPATH}";
                const node = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!node) return null;
                const value = (node.textContent || node.innerText || "").trim();
                return value || null;
            }}
            """
        )
        if not text:
            return None
        return " ".join(str(text).split())

    async def extract_offer_product(self, url: str, include_tempo: bool = False) -> dict:
        assert self.page
        produto = {
            "url_original": url,
            "url_afiliado": None,
            "url_curta": None,
            "product_id": None,
            "mlb_id": None,
            "nome": None,
            "foto_url": None,
            "preco_original": None,
            "preco_atual": None,
            "desconto": None,
            "tempo_para_acabar": None,
            "status": "pendente",
            "erro": None,
        }

        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(900, 1500)
            try:
                await self.page.wait_for_selector("h1, .ui-pdp-title", timeout=10000)
            except Exception:
                pass

            mlb_match = re.search(r"MLB[-]?(\d+)", url)
            if mlb_match:
                produto["mlb_id"] = f"MLB{mlb_match.group(1)}"

            dados = await self.page.evaluate(
                """
                () => {
                    const title = document.querySelector("h1.ui-pdp-title, .ui-pdp-title, h1");
                    const current = document.querySelector(".ui-pdp-price__second-line .andes-money-amount__fraction");
                    const original = document.querySelector(".ui-pdp-price__original-value .andes-money-amount__fraction, s .andes-money-amount__fraction");
                    const discount = document.querySelector(".ui-pdp-price__second-line__label, .andes-money-amount__discount");
                    const image =
                        document.querySelector("main figure img, .ui-pdp-gallery figure img, span figure img, .ui-pdp-gallery__figure img") ||
                        document.querySelector("img[src*='mlstatic'], img[src*='mercadolivre']");

                    return {
                        nome: title?.textContent?.trim() || "",
                        preco_atual: current?.textContent?.trim() || "",
                        preco_original: original?.textContent?.trim() || "",
                        desconto: discount?.textContent?.trim() || "",
                        foto_url: image?.src || image?.getAttribute("data-src") || ""
                    };
                }
                """
            )

            produto["nome"] = dados.get("nome") or None
            produto["foto_url"] = dados.get("foto_url") or None
            produto["preco_atual"] = self._parse_preco(dados.get("preco_atual"))
            produto["preco_original"] = self._parse_preco(dados.get("preco_original"))
            produto["desconto"] = self._parse_desconto(dados.get("desconto"))

            if include_tempo:
                produto["tempo_para_acabar"] = await self._extract_tempo_para_acabar()

            link = await self._extract_link_afiliado()
            if link:
                produto["url_afiliado"] = link.get("url_longa")
                produto["url_curta"] = link.get("url_curta")
                produto["product_id"] = link.get("product_id")
                produto["status"] = "sucesso"
            else:
                produto["status"] = "sem_link"

        except Exception as exc:
            produto["status"] = "erro"
            produto["erro"] = str(exc)

        return produto

    async def _extract_link_afiliado(self) -> Optional[dict]:
        assert self.page
        try:
            btn = None
            try:
                btn = await self.page.wait_for_selector(f"xpath={SHARE_BUTTON_XPATH}", timeout=5000)
            except Exception:
                pass

            if not btn:
                try:
                    btn = await self.page.wait_for_selector(
                        "nav button:has-text('Compartilhar'), header button:has-text('Compartilhar'), button:has-text('Compartilhar')",
                        timeout=5000,
                    )
                except Exception:
                    return None

            await btn.click()
            await self._human_delay(700, 1400)

            try:
                await self.page.wait_for_selector(
                    "input[value*='mercadolivre.com/sec'], input[value*='meli.to'], div:has-text('Link do produto')",
                    timeout=6000,
                )
            except Exception:
                pass

            result: dict[str, str] = {}

            try:
                modal = await self.page.query_selector(f"xpath={SHARE_MODAL_INPUT_XPATH}")
                if modal:
                    input_link = await modal.query_selector("input[type='text'], input[readonly]")
                    if input_link:
                        value = await input_link.get_attribute("value")
                        if value and ("mercadolivre.com/sec/" in value or "meli.to/" in value):
                            result["url_curta"] = value.strip()
            except Exception:
                pass

            if not result.get("url_curta"):
                inputs = await self.page.query_selector_all("input[type='text'], input[readonly]")
                for input_elem in inputs:
                    value = await input_elem.get_attribute("value") or ""
                    if "mercadolivre.com/sec/" in value or "meli.to/" in value:
                        result["url_curta"] = value.strip()
                        break

            if not result.get("url_curta"):
                js_value = await self.page.evaluate(
                    """
                    () => {
                        const all = document.querySelectorAll("*");
                        for (const el of all) {
                            const text = el.textContent || el.innerText || el.value || "";
                            const match = text.match(/(https?:\\/\\/[\\w.-]+\\/sec\\/[\\w-]+)|(https?:\\/\\/meli\\.to\\/[\\w-]+)/);
                            if (match) return match[0];
                        }
                        return null;
                    }
                    """
                )
                if js_value:
                    result["url_curta"] = str(js_value).strip()

            try:
                close_btn = await self.page.query_selector(
                    "[class*='close'], button[aria-label='Fechar'], button:has-text('Fechar')"
                )
                if close_btn:
                    await close_btn.click()
                else:
                    await self.page.keyboard.press("Escape")
            except Exception:
                await self.page.keyboard.press("Escape")

            await self._human_delay(200, 450)
            return result if result.get("url_curta") else None
        except Exception:
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            return None

    async def scrape_coupons(self, max_cupons: int) -> list[dict]:
        assert self.page
        await self.page.goto(CUPONS_URL, wait_until="domcontentloaded", timeout=30000)
        await self._human_delay(1200, 2200)

        try:
            filtro = await self.page.wait_for_selector(f"xpath={CUPONS_FILTER_ACABAM_HOJE_XPATH}", timeout=8000)
            await filtro.click()
            await self._human_delay(1800, 2500)
        except Exception:
            pass

        cards = await self.page.evaluate(
            f"""
            () => {{
                const xpath = "{CUPONS_CARDS_CONTAINER_XPATH}";
                const container = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!container) return [];

                let cardNodes = Array.from(container.children);
                if (!cardNodes.length) {{
                    cardNodes = Array.from(container.querySelectorAll(":scope > *"));
                }}

                const output = [];
                const seen = new Set();

                for (const node of cardNodes) {{
                    const rawText = (node.innerText || node.textContent || "").replace(/\\s+/g, " ").trim();
                    if (!rawText) continue;

                    const uniqueKey = rawText.slice(0, 140);
                    if (seen.has(uniqueKey)) continue;
                    seen.add(uniqueKey);

                    const img = node.querySelector("img");
                    const imagemUrl = img?.src || img?.getAttribute("data-src") || img?.getAttribute("src") || null;

                    const titleNode = node.querySelector("h1, h2, h3, strong, [class*='title'], [class*='coupon']");
                    const nome = (titleNode?.innerText || "").trim() || rawText.slice(0, 120);

                    const descontoMatch = rawText.match(/(\\d+\\s?%|R\\$\\s?[\\d\\.,]+)/i);
                    const descontoTexto = descontoMatch ? descontoMatch[0] : null;

                    const limiteMatch = rawText.match(/(mínimo[^\\.\\n;]*|limite[^\\.\\n;]*|válido[^\\.\\n;]*|até[^\\.\\n;]*)/i);
                    const limite = limiteMatch ? limiteMatch[0] : null;

                    const linkNode = node.querySelector("a[href]");
                    const link = linkNode?.href || "{CUPONS_URL}";

                    output.push({{
                        nome: nome,
                        desconto_texto: descontoTexto,
                        limite_condicoes: limite,
                        imagem_url: imagemUrl,
                        url_origem: link,
                        raw_text: rawText
                    }});
                }}

                return output;
            }}
            """
        )

        return (cards or [])[:max_cupons]

    async def salvar_resultados(self, produtos: list[dict], arquivo: str | None = None) -> str:
        if not arquivo:
            arquivo = f"ofertas_ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(arquivo).write_text(json.dumps(produtos, ensure_ascii=False, indent=2), encoding="utf-8")
        return arquivo
