from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

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
        self.logger = logging.getLogger("scraperofertas.scraper")

    async def __aenter__(self) -> "MercadoLivrePlaywrightScraper":
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._close_browser()

    async def _init_browser(self) -> None:
        self.logger.info(
            "Inicializando browser | headless=%s user_data_dir=%s timezone=%s",
            self.headless,
            self.user_data_dir,
            "America/Sao_Paulo",
        )
        try:
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
            self.logger.info("Browser pronto para scraping")
        except Exception as exc:
            self.logger.error("Falha ao inicializar browser: %s", exc)
            raise

    async def _close_browser(self) -> None:
        self.logger.info("Encerrando browser/contexto")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        self.context = None
        self.playwright = None
        self.page = None
        self.logger.info("Browser encerrado")

    async def _human_delay(self, min_ms: int = 400, max_ms: int = 1200) -> None:
        await asyncio.sleep(random.randint(min_ms, max_ms) / 1000)

    def _is_execution_context_destroyed(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "execution context was destroyed" in message
            or "cannot find context with specified id" in message
            or "most likely because of a navigation" in message
        )

    async def _wait_for_page_stable(self, reason: str, timeout_ms: int = 15000) -> None:
        assert self.page
        for state in ("domcontentloaded", "networkidle"):
            try:
                await self.page.wait_for_load_state(state, timeout=timeout_ms)
            except Exception:
                # Alguns cenarios nao atingem networkidle; nao bloqueia o fluxo.
                pass
        self.logger.info("Pagina estabilizada para seguir | reason=%s", reason)

    async def _evaluate_with_retry(
        self,
        script: str,
        *,
        arg: Any | None = None,
        retries: int = 3,
        reason: str = "evaluate",
    ):
        assert self.page
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                if arg is None:
                    return await self.page.evaluate(script)
                return await self.page.evaluate(script, arg)
            except Exception as exc:
                last_exc = exc
                if self._is_execution_context_destroyed(exc) and attempt < retries:
                    self.logger.warning(
                        "Execution context destruido durante evaluate; retry | reason=%s attempt=%s/%s erro=%s",
                        reason,
                        attempt,
                        retries,
                        exc,
                    )
                    await self._wait_for_page_stable(reason=f"{reason}_retry_{attempt}")
                    await self._human_delay(250, 500)
                    continue
                raise
        if last_exc:
            raise last_exc

    async def _scroll_suave(self, vezes: int = 4) -> None:
        assert self.page
        for _ in range(vezes):
            await self._evaluate_with_retry(
                "window.scrollBy(0, window.innerHeight * 0.8)",
                retries=3,
                reason="scroll_suave_scrollBy",
            )
            await self._human_delay(250, 650)
        await self._evaluate_with_retry(
            "window.scrollTo(0, 0)",
            retries=3,
            reason="scroll_suave_scrollToTop",
        )
        await self._human_delay(200, 400)

    async def verificar_login(self) -> bool:
        assert self.page
        self.logger.info("Verificando sessao de login do afiliado")
        try:
            await self.page.goto(OFFERS_URL, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1000, 1600)

            afiliado_element = await self.page.query_selector(
                "[class*='affiliate'], [class*='nav-affiliate'], :text('Afiliados'), :text('GANHOS')"
            )
            if afiliado_element:
                self.logger.info("Login confirmado via elementos de afiliado")
                return True

            user_element = await self.page.query_selector(
                "[class*='user-name'], [class*='nav-header-user'], :text('Eduardo')"
            )
            logged = bool(user_element)
            self.logger.info("Resultado da verificacao de login | logged=%s", logged)
            return logged
        except Exception as exc:
            self.logger.warning("Falha ao verificar login: %s", exc)
            return False

    async def fazer_login_manual(self) -> bool:
        assert self.page
        self.logger.info("Iniciando fluxo de login manual")
        await self.page.goto("https://www.mercadolivre.com.br", wait_until="domcontentloaded")
        await self._human_delay(800, 1500)
        try:
            login_btn = await self.page.query_selector("a[href*='login'], :text('Entre')")
            if login_btn:
                await login_btn.click()
                self.logger.info("Botao de login clicado")
        except Exception:
            self.logger.warning("Botao de login nao encontrado; aguardando login manual direto")
            pass
        input("Pressione ENTER apos concluir o login manual no navegador...")
        self.logger.info("Confirmacao de usuario recebida; validando login")
        return await self.verificar_login()

    async def _click_relampago_filter(self) -> None:
        assert self.page
        self.logger.info("Tentando clicar no filtro de Ofertas Relampago")
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
            self.logger.info("Filtro de Ofertas Relampago clicado")
            await self._human_delay(2200, 3200)
        else:
            self.logger.warning("Nao foi possivel clicar no filtro de Ofertas Relampago")

    async def _extract_links_from_current_page(self) -> list[str]:
        assert self.page
        links = await self._evaluate_with_retry(
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
            """,
            retries=3,
            reason="extract_links_current_page",
        )
        return links or []

    async def _go_to_next_offers_page(self) -> bool:
        assert self.page
        result = await self._evaluate_with_retry(
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
                        const normalizedText = text.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "");
                        if (normalizedText.includes("proxima") || normalizedText.includes("seguinte") || normalizedText.includes("next")) {{
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
            """,
            retries=3,
            reason="go_to_next_offers_page",
        )
        reason = result.get("reason") if isinstance(result, dict) else "unknown"
        if result and result.get("moved"):
            self.logger.info("Paginacao: avancando para proxima pagina | reason=%s", reason)
            await self._wait_for_page_stable(reason="after_pagination_click")
            await self._human_delay(1000, 1500)
            return True
        self.logger.info("Paginacao: sem avancar | reason=%s", reason)
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
        self.logger.info(
            "Coleta de links iniciada | mode=%s url=%s max_produtos=%s",
            mode,
            base_url,
            max_produtos,
        )
        await self.page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
        await self._human_delay(1200, 1800)

        if mode == "ofertas_relampago":
            await self._click_relampago_filter()

        collected: list[str] = []
        seen_local: set[str] = set()
        max_pages = 20

        for page_index in range(1, max_pages + 1):
            self.logger.info(
                "Lendo pagina de ofertas | mode=%s page=%s coletados_ate_agora=%s",
                mode,
                page_index,
                len(collected),
            )
            try:
                await self._scroll_suave(vezes=5)
                page_links = await self._extract_links_from_current_page()
            except Exception as exc:
                if self._is_execution_context_destroyed(exc):
                    self.logger.warning(
                        "Contexto destruido durante leitura da pagina; aguardando e repetindo passo | mode=%s page=%s erro=%s",
                        mode,
                        page_index,
                        exc,
                    )
                    await self._wait_for_page_stable(reason=f"collect_offer_links_page_{page_index}_retry")
                    await self._scroll_suave(vezes=3)
                    page_links = await self._extract_links_from_current_page()
                else:
                    raise
            if not page_links:
                self.logger.info("Nenhum link encontrado na pagina | mode=%s page=%s", mode, page_index)
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
                    self.logger.info(
                        "Limite de links atingido | mode=%s total=%s",
                        mode,
                        len(collected),
                    )
                    return collected[:max_produtos]

            self.logger.info(
                "Resumo da pagina | mode=%s page=%s links_pagina=%s novos_na_pagina=%s coletados_total=%s",
                mode,
                page_index,
                len(page_links),
                novos_na_pagina,
                len(collected),
            )

            # Regra obrigatoria: se todos da pagina ja vistos, tenta proxima pagina.
            # Para completar max_produtos, tambem avanca de pagina quando ainda ha capacidade.
            if novos_na_pagina == 0 or len(collected) < max_produtos:
                moved = await self._go_to_next_offers_page()
                if not moved:
                    self.logger.info(
                        "Paginacao encerrada | mode=%s page=%s coletados_total=%s",
                        mode,
                        page_index,
                        len(collected),
                    )
                    break
            else:
                break

        self.logger.info("Coleta de links finalizada | mode=%s total=%s", mode, len(collected))
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
        self.logger.info("Extraindo tempo restante da oferta relampago")
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
            self.logger.info("Tempo restante nao encontrado")
            return None
        normalized = " ".join(str(text).split())
        self.logger.info("Tempo restante extraido | valor=%s", normalized)
        return normalized

    async def extract_offer_product(self, url: str, include_tempo: bool = False) -> dict:
        assert self.page
        self.logger.info("Abrindo pagina de produto | url=%s include_tempo=%s", url, include_tempo)
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
            self.logger.error("Erro ao extrair produto | url=%s erro=%s", url, exc)

        self.logger.info(
            "Produto processado no scraper | status=%s mlb_id=%s url=%s",
            produto.get("status"),
            produto.get("mlb_id"),
            url,
        )

        return produto

    async def _extract_link_afiliado(self) -> Optional[dict]:
        assert self.page
        self.logger.info("Iniciando extracao de link afiliado")
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
                    self.logger.warning("Botao Compartilhar nao encontrado")
                    return None

            await btn.click()
            self.logger.info("Botao Compartilhar clicado")
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
            if result.get("url_curta"):
                self.logger.info("Link afiliado extraido com sucesso | url_curta=%s", result.get("url_curta"))
                return result
            self.logger.warning("Nao foi possivel extrair link afiliado apos tentativas")
            return None
        except Exception as exc:
            self.logger.error("Erro durante extracao de link afiliado: %s", exc)
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            return None

    async def _click_cupons_filter_acabam_hoje(self) -> bool:
        assert self.page
        self.logger.info("Tentando aplicar filtro de cupons: 'Acabam hoje'")
        try:
            filtro = await self.page.wait_for_selector(f"xpath={CUPONS_FILTER_ACABAM_HOJE_XPATH}", timeout=8000)
            await filtro.click()
            await self._human_delay(1800, 2500)
            self.logger.info("Filtro 'Acabam hoje' aplicado via XPath")
            return True
        except Exception:
            pass

        clicked = await self._evaluate_with_retry(
            """
            () => {
                const candidates = Array.from(document.querySelectorAll("button, a"));
                const target = candidates.find((el) => {
                    const text = (el.textContent || el.innerText || "").toLowerCase();
                    return text.includes("acabam hoje");
                });
                if (!target) return false;
                target.click();
                return true;
            }
            """,
            retries=3,
            reason="click_cupons_filter_fallback",
        )
        if clicked:
            await self._human_delay(1800, 2500)
            self.logger.info("Filtro 'Acabam hoje' aplicado via fallback textual")
        else:
            self.logger.warning("Nao foi possivel aplicar filtro 'Acabam hoje'")
        return bool(clicked)

    async def _extract_coupon_candidates(self) -> list[dict]:
        assert self.page
        script = """
        () => {
            const xpath = "__XPATH__";
            const xpathRoot = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;

            const roots = [];
            if (xpathRoot) roots.push(xpathRoot);
            if (xpathRoot?.parentElement) roots.push(xpathRoot.parentElement);
            const main = document.querySelector("main");
            if (main) roots.push(main);
            if (!roots.length) roots.push(document.body);

            const nodeSelectors = [
                "[data-testid*='coupon' i]",
                "[class*='coupon' i]",
                "article",
                "li",
                "[class*='card' i]",
                "[class*='andes-card' i]",
                "div"
            ];

            const rawCandidates = [];
            const seen = new Set();

            for (const root of roots) {
                for (const selector of nodeSelectors) {
                    const nodes = root.querySelectorAll(selector);
                    for (const node of nodes) {
                        if (!(node instanceof HTMLElement)) continue;
                        if (seen.has(node)) continue;
                        seen.add(node);

                        const rawText = (node.innerText || node.textContent || "").replace(/\\s+/g, " ").trim();
                        if (!rawText || rawText.length < 8) continue;

                        const hasDiscount = /(\\d{1,3}\\s?%|R\\$\\s?[\\d\\.,]+)/i.test(rawText);
                        const hasCouponWord = /cupom|coupon/i.test(rawText);
                        if (!hasDiscount && !hasCouponWord) continue;

                        const titleNode = node.querySelector(
                            "h1, h2, h3, strong, [class*='title' i], [class*='name' i], [class*='coupon' i]"
                        );
                        const linkNode = node.querySelector("a[href]");
                        const imageNode = node.querySelector("img");
                        const svgNode = node.querySelector(".badge svg") || node.querySelector("svg");
                        const svgOuterHtml = svgNode?.outerHTML || null;
                        const imagemUrlTradicional = imageNode?.src || imageNode?.getAttribute("data-src") || null;
                        const imagemDataUri = svgOuterHtml
                            ? `data:image/svg+xml;utf8,${encodeURIComponent(svgOuterHtml)}`
                            : null;

                        const descontoMatch = rawText.match(/(\\d{1,3}\\s?%|R\\$\\s?[\\d\\.,]+)/i);
                        const limiteMatch = rawText.match(
                            /(m[i\\u00ED]nimo[^\\.\\n;]*|limite[^\\.\\n;]*|v[a\\u00E1]lido[^\\.\\n;]*|at[e\\u00E9][^\\.\\n;]*)/i
                        );

                            rawCandidates.push({
                                nome: (titleNode?.innerText || "").trim() || null,
                                desconto_texto: descontoMatch ? descontoMatch[0] : null,
                                limite_condicoes: limiteMatch ? limiteMatch[0] : null,
                                imagem_url: imagemDataUri || imagemUrlTradicional || null,
                                imagem_svg_html: svgOuterHtml,
                                imagem_data_uri: imagemDataUri,
                                imagem_tipo: imagemDataUri ? "svg_data_uri" : (imagemUrlTradicional ? "url" : null),
                                url_origem: linkNode?.href || "__CUPONS_URL__",
                                raw_text: rawText,
                            });
                    }
                }
            }

            return rawCandidates;
        }
        """
        script = script.replace("__XPATH__", CUPONS_CARDS_CONTAINER_XPATH).replace("__CUPONS_URL__", CUPONS_URL)
        return await self._evaluate_with_retry(
            script,
            retries=3,
            reason="extract_coupon_candidates",
        )

    def _build_svg_data_uri(self, svg_outer_html: str | None) -> str | None:
        if not svg_outer_html:
            return None
        compact = " ".join(str(svg_outer_html).split())
        if not compact:
            return None
        return f"data:image/svg+xml;utf8,{quote(compact, safe='')}"

    def _normalize_coupon_candidates(self, raw_cards: list[dict], max_cupons: int) -> list[dict]:
        normalized: list[dict] = []
        seen_signatures: set[str] = set()

        for idx, raw in enumerate(raw_cards or [], start=1):
            if not isinstance(raw, dict):
                continue

            raw_text = " ".join(str(raw.get("raw_text") or "").split())
            nome = " ".join(str(raw.get("nome") or "").split()) or None
            desconto_texto = " ".join(str(raw.get("desconto_texto") or "").split()) or None
            limite_condicoes = " ".join(str(raw.get("limite_condicoes") or "").split()) or None
            imagem_url = str(raw.get("imagem_url") or "").strip() or None
            imagem_svg_html = str(raw.get("imagem_svg_html") or "").strip() or None
            imagem_data_uri = str(raw.get("imagem_data_uri") or "").strip() or None
            imagem_tipo = str(raw.get("imagem_tipo") or "").strip() or None
            url_origem = str(raw.get("url_origem") or "").strip() or CUPONS_URL

            if not imagem_data_uri:
                imagem_data_uri = self._build_svg_data_uri(imagem_svg_html)
            if imagem_data_uri:
                imagem_url = imagem_data_uri
                imagem_tipo = "svg_data_uri"
            elif not imagem_tipo and imagem_url:
                imagem_tipo = "url"

            if not desconto_texto and raw_text:
                match = re.search(r"(\d{1,3}\s?%|R\$\s?[\d\.,]+)", raw_text, flags=re.IGNORECASE)
                if match:
                    desconto_texto = match.group(1)

            if not nome and raw_text:
                nome = raw_text[:160]

            if not raw_text and not nome and not desconto_texto:
                continue

            signature = "|".join(
                [
                    (nome or "").lower(),
                    (desconto_texto or "").lower(),
                    url_origem.lower(),
                    (imagem_url or "").lower()[:160],
                    raw_text.lower()[:180],
                ]
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            normalized.append(
                {
                    "nome": nome,
                    "desconto_texto": desconto_texto,
                    "limite_condicoes": limite_condicoes,
                    "imagem_url": imagem_url,
                    "imagem_svg_html": imagem_svg_html,
                    "imagem_data_uri": imagem_data_uri,
                    "imagem_tipo": imagem_tipo,
                    "url_origem": url_origem,
                    "raw_text": raw_text,
                }
            )
            self.logger.info(
                "Card de cupom normalizado | index=%s possui_svg=%s possui_imagem=%s imagem_tipo=%s",
                idx,
                bool(imagem_data_uri),
                bool(imagem_url),
                imagem_tipo or "none",
            )
            if len(normalized) >= max_cupons:
                break

        return normalized

    async def scrape_coupons(self, max_cupons: int) -> list[dict]:
        assert self.page
        self.logger.info("Iniciando scraping de cupons | url=%s max_cupons=%s", CUPONS_URL, max_cupons)
        await self.page.goto(CUPONS_URL, wait_until="domcontentloaded", timeout=30000)
        await self._human_delay(1200, 2200)

        filtro_aplicado = await self._click_cupons_filter_acabam_hoje()
        self.logger.info("Resultado de aplicacao do filtro de cupons | aplicado=%s", filtro_aplicado)

        for _ in range(5):
            await self._evaluate_with_retry(
                "window.scrollBy(0, window.innerHeight * 0.85)",
                retries=3,
                reason="scrape_coupons_scrollBy",
            )
            await self._human_delay(250, 650)
        await self._evaluate_with_retry(
            "window.scrollTo(0, 0)",
            retries=3,
            reason="scrape_coupons_scrollToTop",
        )
        await self._human_delay(300, 700)
        self.logger.info("Scroll inicial de cupons concluido")

        raw_cards = await self._extract_coupon_candidates()
        self.logger.info("Cards de cupons candidatos coletados | total_raw=%s", len(raw_cards))

        if len(raw_cards) < max_cupons:
            await self._evaluate_with_retry(
                "window.scrollTo(0, document.body.scrollHeight)",
                retries=3,
                reason="scrape_coupons_scrollToBottom",
            )
            await self._human_delay(800, 1500)
            raw_second_pass = await self._extract_coupon_candidates()
            raw_cards.extend(raw_second_pass)
            self.logger.info(
                "Segunda coleta de cupons executada | total_novos=%s total_acumulado=%s",
                len(raw_second_pass),
                len(raw_cards),
            )

        normalized = self._normalize_coupon_candidates(raw_cards=raw_cards or [], max_cupons=max_cupons)
        total_svg = sum(1 for item in normalized if item.get("imagem_tipo") == "svg_data_uri")
        total_sem_imagem = sum(1 for item in normalized if not item.get("imagem_url"))
        self.logger.info(
            "Resumo de imagens de cupons | total=%s com_svg=%s sem_imagem=%s",
            len(normalized),
            total_svg,
            total_sem_imagem,
        )
        if total_sem_imagem:
            self.logger.warning(
                "Cupons sem imagem identificados | quantidade=%s (sem SVG e sem URL de imagem)",
                total_sem_imagem,
            )
        self.logger.info("Scraping de cupons finalizado | total_normalizado=%s", len(normalized))
        return normalized

    async def salvar_resultados(self, produtos: list[dict], arquivo: str | None = None) -> str:
        if not arquivo:
            arquivo = f"ofertas_ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(arquivo).write_text(json.dumps(produtos, ensure_ascii=False, indent=2), encoding="utf-8")
        return arquivo
