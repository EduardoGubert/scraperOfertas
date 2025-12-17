"""
Scraper de Ofertas e Cupons - Magazine Você, Magalu, Mercado Livre, Shopee
Autor: Eduardo (egnOfertas)
Usa Playwright para JavaScript Rendering
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from playwright.async_api import async_playwright, Page, Browser


class ScraperOfertas:
    """Scraper genérico para e-commerces brasileiros"""
    
    def __init__(self, wait_ms: int = 1000, headless: bool = True, affiliate_config: dict = None):
        self.wait_ms = wait_ms
        self.headless = headless
        self.browser: Optional[Browser] = None
        
        # Configuração de afiliados
        self.affiliate_config = affiliate_config or {}
        # Exemplo de config:
        # {
        #     "mercadolivre": {
        #         "base_url": "https://www.mercadolivre.com.br/social/eduardogubertnascimento",
        #         "params": {"matt_tool": "39349855", "matt_word": "egnofertas"}
        #     },
        #     "magazinevoce": {
        #         "showcase": "magazinegubert"
        #     }
        # }
        
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

    def _add_affiliate_link(self, url: str, source: str) -> str:
        """Adiciona parâmetros de afiliado à URL"""
        if not self.affiliate_config or source not in self.affiliate_config:
            return url
        
        config = self.affiliate_config[source]
        
        if source == "mercadolivre" and "base_url" in config:
            # Para ML, usa o formato de link de afiliado
            # Mantém a URL original mas pode adicionar tracking
            params = config.get("params", {})
            if params:
                separator = "&" if "?" in url else "?"
                param_string = urlencode(params)
                return f"{url}{separator}{param_string}"
        
        return url

    # ============================================
    # CUPONS
    # ============================================
    
    async def scrape_cupons_magazine(self, showcase: str = "magazinegubert") -> list[dict]:
        """
        Scraper de cupons do Magazine Você
        
        Args:
            showcase: ID da sua loja (ex: magazinegubert)
            
        Returns:
            Lista de cupons com código, desconto, categoria e imagem
        """
        url = f"https://especiais.magazineluiza.com.br/magazinevoce/cupons/?showcase={showcase}"
        page = await self._create_page()
        cupons = []
        
        try:
            print(f"🔄 Buscando cupons: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(self.wait_ms)
            
            # Extrai cupons via JavaScript
            cupons = await page.evaluate("""
                () => {
                    const cupons = [];
                    const images = document.querySelectorAll('img[src*="pmd_"]');
                    
                    images.forEach(img => {
                        const src = img.src || '';
                        const filename = src.split('/').pop().split('.')[0];
                        
                        // Extrai informações do nome do arquivo
                        // Formato: pmd_categoria_desconto_data
                        // Ex: pmd_cozinha50_021225 = 50% off em cozinha
                        const parts = filename.replace('pmd_', '').split('_');
                        
                        if (parts.length >= 1) {
                            // Extrai categoria e desconto
                            const catDesc = parts[0];
                            const match = catDesc.match(/([a-z]+)(\d+)/i);
                            
                            if (match) {
                                const categoria = match[1];
                                const desconto = match[2];
                                
                                // Tenta extrair código do cupom (geralmente está na imagem)
                                // O código real precisa ser clicado, então salvamos a referência
                                cupons.push({
                                    categoria: categoria.toUpperCase(),
                                    desconto: desconto + '%',
                                    codigo: catDesc.toUpperCase(),
                                    imagem: src,
                                    tipo: 'magazine'
                                });
                            } else if (catDesc.toLowerCase() === 'bemvindo') {
                                cupons.push({
                                    categoria: 'BOAS VINDAS',
                                    desconto: 'Especial',
                                    codigo: 'BEMVINDO',
                                    imagem: src,
                                    tipo: 'magazine'
                                });
                            }
                        }
                    });
                    
                    return cupons;
                }
            """)
            
            print(f"✅ Encontrados {len(cupons)} cupons")
            
        except Exception as e:
            print(f"❌ Erro ao buscar cupons Magazine: {e}")
        finally:
            await page.close()
            
        return cupons

    async def scrape_cupons_mercadolivre(self) -> list[dict]:
        """
        Scraper de cupons do Mercado Livre
        
        Returns:
            Lista de cupons disponíveis
        """
        url = "https://www.mercadolivre.com.br/cupons"
        page = await self._create_page()
        cupons = []
        
        try:
            print(f"🔄 Buscando cupons ML: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(self.wait_ms * 2)
            await self._scroll_page(page)
            
            # Extrai cupons via JavaScript
            cupons = await page.evaluate("""
                () => {
                    const cupons = [];
                    
                    // Seletores possíveis para cupons do ML
                    const cards = document.querySelectorAll('[class*="coupon"], [class*="Coupon"], [data-testid*="coupon"]');
                    
                    cards.forEach(card => {
                        try {
                            const title = card.querySelector('[class*="title"], h2, h3');
                            const discount = card.querySelector('[class*="discount"], [class*="value"]');
                            const code = card.querySelector('[class*="code"], button');
                            const img = card.querySelector('img');
                            
                            cupons.push({
                                categoria: title?.textContent?.trim() || 'Geral',
                                desconto: discount?.textContent?.trim() || '',
                                codigo: code?.textContent?.trim() || 'VER CUPOM',
                                imagem: img?.src || '',
                                tipo: 'mercadolivre'
                            });
                        } catch(e) {}
                    });
                    
                    // Se não encontrou com seletores específicos, tenta genérico
                    if (cupons.length === 0) {
                        const allCards = document.querySelectorAll('[class*="card"], [class*="Card"]');
                        allCards.forEach(card => {
                            const text = card.textContent || '';
                            if (text.includes('%') || text.includes('OFF') || text.includes('R$')) {
                                const img = card.querySelector('img');
                                cupons.push({
                                    categoria: 'Oferta',
                                    desconto: text.match(/(\d+%|\d+\s*OFF|R\$\s*\d+)/i)?.[0] || '',
                                    codigo: 'VER OFERTA',
                                    imagem: img?.src || '',
                                    tipo: 'mercadolivre'
                                });
                            }
                        });
                    }
                    
                    return cupons;
                }
            """)
            
            print(f"✅ Encontrados {len(cupons)} cupons ML")
            
        except Exception as e:
            print(f"❌ Erro ao buscar cupons ML: {e}")
        finally:
            await page.close()
            
        return cupons

    async def scrape_ofertas_mercadolivre(self) -> list[dict]:
        """
        Scraper da página de ofertas do Mercado Livre
        
        Returns:
            Lista de produtos em oferta
        """
        url = "https://www.mercadolivre.com.br/ofertas"
        page = await self._create_page()
        produtos = []
        
        try:
            print(f"🔄 Buscando ofertas ML: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(self.wait_ms)
            await self._scroll_page(page, scroll_count=5)
            
            # Extrai ofertas via JavaScript
            produtos = await page.evaluate("""
                () => {
                    const produtos = [];
                    
                    // Seletores da página de ofertas do ML
                    const items = document.querySelectorAll('.promotion-item, .poly-card, [class*="promotion"], [class*="deal"]');
                    
                    items.forEach(item => {
                        try {
                            const img = item.querySelector('img');
                            const title = item.querySelector('[class*="title"], .poly-card__title, h2, h3');
                            const originalPrice = item.querySelector('[class*="original"], [class*="from"], s, del');
                            const currentPrice = item.querySelector('[class*="current"], [class*="price"]:not([class*="original"]), .andes-money-amount');
                            const discount = item.querySelector('[class*="discount"], [class*="off"]');
                            const link = item.querySelector('a') || item.closest('a');
                            
                            // Extrai preço atual
                            let preco = '';
                            if (currentPrice) {
                                const fraction = currentPrice.querySelector('.andes-money-amount__fraction');
                                if (fraction) {
                                    preco = 'R$ ' + fraction.textContent.trim();
                                } else {
                                    preco = currentPrice.textContent.trim();
                                }
                            }
                            
                            if (title || img) {
                                produtos.push({
                                    foto: img?.src || '',
                                    nome: title?.textContent?.trim() || img?.alt || '',
                                    preço: preco,
                                    preço_original: originalPrice?.textContent?.trim() || '',
                                    desconto: discount?.textContent?.trim() || '',
                                    url: link?.href || ''
                                });
                            }
                        } catch(e) {}
                    });
                    
                    return produtos;
                }
            """)
            
            # Adiciona links de afiliado
            produtos = [
                {**p, 'url': self._add_affiliate_link(p['url'], 'mercadolivre')}
                for p in produtos
            ]
            
            print(f"✅ Encontradas {len(produtos)} ofertas ML")
            
        except Exception as e:
            print(f"❌ Erro ao buscar ofertas ML: {e}")
        finally:
            await page.close()
            
        return produtos

    # ============================================
    # PRODUTOS (mantém os métodos originais)
    # ============================================

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
                '[data-testid="product-card"]',
                '.product-card',
                'li[class*="product"]',
                'a[class*="product"]',
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
        
        img = await element.query_selector('img')
        if img:
            produto['foto'] = await img.get_attribute('src') or await img.get_attribute('data-src') or ''
        
        for selector in ['h2', 'h3', '[class*="title"]', '[class*="name"]']:
            title_el = await element.query_selector(selector)
            if title_el:
                produto['nome'] = (await title_el.text_content() or '').strip()
                if produto['nome']:
                    break
        
        if not produto['nome'] and img:
            produto['nome'] = await img.get_attribute('alt') or ''
        
        for selector in ['[class*="price"]', '[class*="Price"]', '[data-testid*="price"]']:
            price_el = await element.query_selector(selector)
            if price_el:
                produto['preço'] = (await price_el.text_content() or '').strip()
                if produto['preço']:
                    break
        
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
            
            items = await page.query_selector_all('.ui-search-layout__item, .andes-card')
            
            if not items:
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
            
            # Adiciona links de afiliado
            produtos = [
                {**p, 'url': self._add_affiliate_link(p['url'], 'mercadolivre')}
                for p in produtos
            ]
                        
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
        """Scraper específico para Shopee"""
        page = await self._create_page()
        produtos = []
        
        try:
            print(f"🔄 Acessando Shopee: {url}")
            await page.goto(url, wait_until='networkidle', timeout=45000)
            await page.wait_for_timeout(self.wait_ms * 2)
            await self._scroll_page(page, scroll_count=5)
            
            produtos = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('[data-sqe="item"], .shopee-search-item-result__item, .shop-search-result-view__item');
                    return Array.from(items).map(item => {
                        const img = item.querySelector('img');
                        const title = item.querySelector('.Cve6sh, .ie3A\\+n, [data-sqe="name"]');
                        const price = item.querySelector('.ZEgDH9, .k9JZlv, [class*="price"]');
                        const link = item.querySelector('a');
                        
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
        """Scraper específico para Amazon Brasil"""
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
        await page.evaluate('window.scrollTo(0, 0)')
        await page.wait_for_timeout(300)

    async def scrape_auto(self, url: str) -> list[dict]:
        """
        Detecta automaticamente o site e usa o scraper correto
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
            return await self.scrape_magazine_voce(url)


async def main():
    """Exemplo de uso com cupons"""
    
    # Configuração de afiliado
    affiliate_config = {
        "mercadolivre": {
            "params": {"matt_tool": "39349855", "matt_word": "egnofertas"}
        },
        "magazinevoce": {
            "showcase": "magazinegubert"
        }
    }
    
    async with ScraperOfertas(wait_ms=1500, headless=True, affiliate_config=affiliate_config) as scraper:
        # Buscar cupons Magazine
        print("\n" + "="*60)
        print("🎟️  CUPONS MAGAZINE VOCÊ")
        print("="*60)
        cupons = await scraper.scrape_cupons_magazine("magazinegubert")
        for c in cupons[:5]:
            print(f"  • {c['categoria']}: {c['desconto']} - Código: {c['codigo']}")
        
        # Buscar ofertas ML
        print("\n" + "="*60)
        print("🛒 OFERTAS MERCADO LIVRE")
        print("="*60)
        ofertas = await scraper.scrape_ofertas_mercadolivre()
        for o in ofertas[:5]:
            print(f"  • {o['nome'][:40]}... - {o['preço']}")


if __name__ == "__main__":
    asyncio.run(main())