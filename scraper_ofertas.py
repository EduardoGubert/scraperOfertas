"""
Scraper de Ofertas - Magazine Você, Magalu, Mercado Livre, Shopee
Autor: Eduardo (egnOfertas)
Usa Playwright para JavaScript Rendering
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser


class ScraperOfertas:
    """Scraper genérico para e-commerces brasileiros"""
    
    def __init__(self, wait_ms: int = 1000, headless: bool = True):
        self.wait_ms = wait_ms
        self.headless = headless
        self.browser: Optional[Browser] = None
        
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()

    async def _create_page(self) -> Page:
        """Cria página com configurações anti-detecção"""
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo'
        )
        page = await context.new_page()
        
        # Remove webdriver flag
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return page

    async def scrape_magazine_voce(self, url: str) -> list[dict]:
        """
        Scraper específico para Magazine Você / Magalu
        
        Args:
            url: URL da página de ofertas
            
        Returns:
            Lista de produtos com foto, nome, preço e url
        """
        page = await self._create_page()
        produtos = []
        
        try:
            print(f"🔄 Acessando: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(self.wait_ms)
            
            # Scroll para carregar lazy loading
            await self._scroll_page(page)
            
            # Seletores do Magazine Você/Magalu
            selectors = [
                # Estrutura principal
                '[data-testid="product-card"]',
                '.product-card',
                'li[class*="product"]',
                'a[class*="product"]',
                # Fallback genérico
                '[class*="ProductCard"]',
                '[class*="productCard"]'
            ]
            
            product_elements = []
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    product_elements = elements
                    print(f"✅ Encontrados {len(elements)} produtos com seletor: {selector}")
                    break
            
            if not product_elements:
                # Tenta extrair via JavaScript
                produtos = await self._extract_via_js_magazine(page)
            else:
                for element in product_elements:
                    try:
                        produto = await self._parse_product_magazine(element, page)
                        if produto and produto.get('nome'):
                            produtos.append(produto)
                    except Exception as e:
                        print(f"⚠️ Erro ao parsear produto: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Erro no scraping: {e}")
        finally:
            await page.close()
            
        return produtos

    async def _extract_via_js_magazine(self, page: Page) -> list[dict]:
        """Extrai produtos via JavaScript direto no DOM"""
        return await page.evaluate("""
            () => {
                const produtos = [];
                
                // Tenta múltiplas estratégias
                const cards = document.querySelectorAll('a[href*="/p/"]');
                
                cards.forEach(card => {
                    try {
                        const img = card.querySelector('img');
                        const priceEl = card.querySelector('[class*="price"], [class*="Price"], [data-testid*="price"]');
                        const titleEl = card.querySelector('[class*="title"], [class*="Title"], h2, h3, [data-testid*="title"]');
                        
                        if (img || titleEl) {
                            produtos.push({
                                foto: img?.src || img?.dataset?.src || '',
                                nome: titleEl?.textContent?.trim() || img?.alt || '',
                                preço: priceEl?.textContent?.trim() || '',
                                url: card.href || ''
                            });
                        }
                    } catch(e) {}
                });
                
                return produtos;
            }
        """)

    async def _parse_product_magazine(self, element, page: Page) -> dict:
        """Parseia um elemento de produto do Magazine"""
        produto = {
            'foto': '',
            'nome': '',
            'preço': '',
            'url': ''
        }
        
        # Foto
        img = await element.query_selector('img')
        if img:
            produto['foto'] = await img.get_attribute('src') or await img.get_attribute('data-src') or ''
        
        # Nome
        for selector in ['h2', 'h3', '[class*="title"]', '[class*="name"]']:
            title_el = await element.query_selector(selector)
            if title_el:
                produto['nome'] = (await title_el.text_content() or '').strip()
                if produto['nome']:
                    break
        
        # Se não achou título, tenta alt da imagem
        if not produto['nome'] and img:
            produto['nome'] = await img.get_attribute('alt') or ''
        
        # Preço
        for selector in ['[class*="price"]', '[class*="Price"]', '[data-testid*="price"]']:
            price_el = await element.query_selector(selector)
            if price_el:
                produto['preço'] = (await price_el.text_content() or '').strip()
                if produto['preço']:
                    break
        
        # URL
        link = await element.query_selector('a') if await element.get_attribute('href') is None else element
        if link:
            href = await link.get_attribute('href')
            if href:
                produto['url'] = href if href.startswith('http') else href
        
        return produto

    async def scrape_mercado_livre(self, url: str) -> list[dict]:
        """
        Scraper específico para Mercado Livre
        
        Args:
            url: URL da página de busca/ofertas
            
        Returns:
            Lista de produtos
        """
        page = await self._create_page()
        produtos = []
        
        try:
            print(f"🔄 Acessando Mercado Livre: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(self.wait_ms)
            await self._scroll_page(page)
            
            # Seletores do ML
            items = await page.query_selector_all('.ui-search-layout__item, .andes-card')
            
            if not items:
                # Extração via JS
                produtos = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('.ui-search-layout__item, .andes-card');
                        return Array.from(items).map(item => {
                            const img = item.querySelector('img');
                            const title = item.querySelector('.ui-search-item__title, .poly-card__title');
                            const price = item.querySelector('.andes-money-amount__fraction, .poly-price__current');
                            const link = item.querySelector('a.ui-search-link, a.poly-card__portada');
                            
                            return {
                                foto: img?.src || '',
                                nome: title?.textContent?.trim() || '',
                                preço: price ? 'R$ ' + price.textContent?.trim() : '',
                                url: link?.href || ''
                            };
                        }).filter(p => p.nome);
                    }
                """)
            else:
                for item in items:
                    produto = await self._parse_product_ml(item)
                    if produto.get('nome'):
                        produtos.append(produto)
                        
        except Exception as e:
            print(f"❌ Erro no ML: {e}")
        finally:
            await page.close()
            
        return produtos

    async def _parse_product_ml(self, element) -> dict:
        """Parseia produto do Mercado Livre"""
        produto = {'foto': '', 'nome': '', 'preço': '', 'url': ''}
        
        img = await element.query_selector('img')
        if img:
            produto['foto'] = await img.get_attribute('src') or ''
        
        title = await element.query_selector('.ui-search-item__title, .poly-card__title, h2')
        if title:
            produto['nome'] = (await title.text_content() or '').strip()
        
        price = await element.query_selector('.andes-money-amount__fraction, .poly-price__current')
        if price:
            produto['preço'] = f"R$ {(await price.text_content() or '').strip()}"
        
        link = await element.query_selector('a')
        if link:
            produto['url'] = await link.get_attribute('href') or ''
        
        return produto

    async def scrape_shopee(self, url: str) -> list[dict]:
        """
        Scraper específico para Shopee
        
        Args:
            url: URL da página
            
        Returns:
            Lista de produtos
        """
        page = await self._create_page()
        produtos = []
        
        try:
            print(f"🔄 Acessando Shopee: {url}")
            await page.goto(url, wait_until='networkidle', timeout=45000)
            await page.wait_for_timeout(self.wait_ms * 2)  # Shopee é mais lento
            await self._scroll_page(page, scroll_count=5)
            
            # Extração via JS (Shopee usa React pesado)
            produtos = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('[data-sqe="item"], .shopee-search-item-result__item, .shop-search-result-view__item');
                    return Array.from(items).map(item => {
                        const img = item.querySelector('img');
                        const title = item.querySelector('.Cve6sh, .ie3A\\+n, [data-sqe="name"]');
                        const price = item.querySelector('.ZEgDH9, .k9JZlv, [class*="price"]');
                        const link = item.querySelector('a');
                        
                        // Limpa preço (remove "R$" duplicados, etc)
                        let preco = price?.textContent?.trim() || '';
                        if (!preco.includes('R$')) preco = 'R$ ' + preco;
                        
                        return {
                            foto: img?.src || '',
                            nome: title?.textContent?.trim() || '',
                            preço: preco,
                            url: link?.href || ''
                        };
                    }).filter(p => p.nome);
                }
            """)
            
        except Exception as e:
            print(f"❌ Erro na Shopee: {e}")
        finally:
            await page.close()
            
        return produtos

    async def scrape_amazon(self, url: str) -> list[dict]:
        """
        Scraper específico para Amazon Brasil
        """
        page = await self._create_page()
        produtos = []
        
        try:
            print(f"🔄 Acessando Amazon: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(self.wait_ms)
            await self._scroll_page(page)
            
            produtos = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('[data-component-type="s-search-result"], .s-result-item');
                    return Array.from(items).map(item => {
                        const img = item.querySelector('img.s-image');
                        const title = item.querySelector('h2 a span, .a-text-normal');
                        const priceWhole = item.querySelector('.a-price-whole');
                        const priceFraction = item.querySelector('.a-price-fraction');
                        const link = item.querySelector('h2 a, a.a-link-normal');
                        
                        let preco = '';
                        if (priceWhole) {
                            preco = 'R$ ' + priceWhole.textContent.replace('.', '').trim();
                            if (priceFraction) preco += ',' + priceFraction.textContent.trim();
                        }
                        
                        return {
                            foto: img?.src || '',
                            nome: title?.textContent?.trim() || '',
                            preço: preco,
                            url: link?.href ? (link.href.startsWith('http') ? link.href : 'https://www.amazon.com.br' + link.href) : ''
                        };
                    }).filter(p => p.nome && !p.nome.includes('Patrocinado'));
                }
            """)
            
        except Exception as e:
            print(f"❌ Erro na Amazon: {e}")
        finally:
            await page.close()
            
        return produtos

    async def _scroll_page(self, page: Page, scroll_count: int = 3):
        """Scroll para carregar lazy loading"""
        for i in range(scroll_count):
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await page.wait_for_timeout(500)
        # Volta pro topo
        await page.evaluate('window.scrollTo(0, 0)')
        await page.wait_for_timeout(300)

    async def scrape_auto(self, url: str) -> list[dict]:
        """
        Detecta automaticamente o site e usa o scraper correto
        
        Args:
            url: Qualquer URL de e-commerce
            
        Returns:
            Lista de produtos
        """
        url_lower = url.lower()
        
        if 'magazinevoce' in url_lower or 'magazineluiza' in url_lower or 'magalu' in url_lower:
            return await self.scrape_magazine_voce(url)
        elif 'mercadolivre' in url_lower or 'mercadolibre' in url_lower:
            return await self.scrape_mercado_livre(url)
        elif 'shopee' in url_lower:
            return await self.scrape_shopee(url)
        elif 'amazon' in url_lower:
            return await self.scrape_amazon(url)
        else:
            print(f"⚠️ Site não reconhecido, tentando scraper genérico...")
            return await self.scrape_magazine_voce(url)  # Tenta genérico


async def main():
    """Exemplo de uso"""
    
    # URLs para testar
    urls = [
        "https://www.magazinevoce.com.br/magazinegubert/selecao/ofertasdodia/?sortOrientation=desc&sortType=soldQuantity&filters=review---4",
        # "https://lista.mercadolivre.com.br/ofertas",
        # "https://shopee.com.br/flash_sale",
    ]
    
    async with ScraperOfertas(wait_ms=1500, headless=True) as scraper:
        for url in urls:
            print(f"\n{'='*60}")
            print(f"📦 Scraping: {url[:60]}...")
            print('='*60)
            
            produtos = await scraper.scrape_auto(url)
            
            print(f"\n✅ Total de produtos encontrados: {len(produtos)}")
            
            # Salva em JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"produtos_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(produtos, f, ensure_ascii=False, indent=4)
            
            print(f"💾 Salvo em: {filename}")
            
            # Preview dos primeiros 3
            print("\n📋 Preview dos primeiros produtos:")
            for i, p in enumerate(produtos[:3], 1):
                print(f"\n{i}. {p['nome'][:50]}...")
                print(f"   💰 {p['preço']}")
                print(f"   🔗 {p['url'][:60]}...")


if __name__ == "__main__":
    asyncio.run(main())
