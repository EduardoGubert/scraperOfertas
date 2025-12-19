"""
Scraper de Ofertas do Mercado Livre com Login de Afiliado
Autor: Eduardo (egnOfertas)

Fluxo:
1. Login uma vez (salva cookies)
2. Navega até ofertas
3. Para cada produto: clica → compartilha → extrai link de afiliado
4. Retorna dados completos com link curto de afiliado
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class ScraperMLAfiliado:
    """Scraper do Mercado Livre com autenticação de afiliado"""
    
    # Configurações
    COOKIES_FILE = "ml_cookies.json"
    USER_DATA_DIR = "./ml_browser_data"
    
    # URLs
    URL_LOGIN = "https://www.mercadolivre.com.br/login"
    URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas"
    URL_OFERTAS_RELAMPAGO = "https://www.mercadolivre.com.br/ofertas#nav-header"
    
    # Seletores (atualizados baseado nas imagens)
    SELECTORS = {
        # Página de ofertas
        "produto_card": ".promotion-item, .poly-card, [class*='poly-card'], .andes-card",
        "produto_link": "a[href*='/p/'], a[href*='MLB']",
        "produto_nome": ".poly-card__title, .ui-search-item__title, h2",
        "produto_preco": ".andes-money-amount__fraction, .poly-price__current .andes-money-amount__fraction",
        "produto_preco_original": ".andes-money-amount--previous .andes-money-amount__fraction, s .andes-money-amount__fraction",
        "produto_desconto": "[class*='discount'], .poly-price__off, .andes-money-amount__discount",
        "produto_foto": "img[src*='mlstatic'], img[data-src*='mlstatic']",
        
        # Barra de afiliados (dentro da página do produto)
        "barra_afiliados": "[class*='affiliate'], [class*='Afiliados']",
        "btn_compartilhar": "button:has-text('Compartilhar'), [class*='share'] button, a:has-text('Compartilhar')",
        
        # Modal de compartilhar
        "modal_link": "input[type='text'][value*='mercadolivre.com/sec'], [class*='link'] input",
        "modal_link_texto": "[class*='link-text'], [class*='copyable']",
        "modal_close": "[class*='close'], button[aria-label='Fechar']",
        
        # Login
        "input_email": "input[name='user_id'], input[type='email'], #user_id",
        "input_senha": "input[name='password'], input[type='password'], #password",
        "btn_continuar": "button[type='submit'], button:has-text('Continuar')",
        "btn_entrar": "button[type='submit'], button:has-text('Entrar')",
    }
    
    def __init__(
        self, 
        headless: bool = False,  # False para ver o navegador durante login
        wait_ms: int = 1500,
        max_produtos: int = 50,
        etiqueta: str = "egnofertas"
    ):
        self.headless = headless
        self.wait_ms = wait_ms
        self.max_produtos = max_produtos
        self.etiqueta = etiqueta
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def __aenter__(self):
        await self._init_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_browser()
    
    async def _init_browser(self):
        """Inicializa o browser com contexto persistente e anti-detecção avançada"""
        self.playwright = await async_playwright().start()
        
        # Usa contexto persistente para manter login
        # IMPORTANTE: channel="chrome" usa o Chrome real instalado (melhor para CAPTCHA)
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.USER_DATA_DIR,
            headless=self.headless,
            channel="chrome",  # Usa Chrome real ao invés do Chromium
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            geolocation={'latitude': -23.5505, 'longitude': -46.6333},  # São Paulo
            permissions=['geolocation'],
            color_scheme='light',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-infobars',
                '--disable-extensions',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--start-maximized',
                # Flags importantes para reCAPTCHA
                '--disable-features=IsolateOrigins,site-per-process',
                '--enable-features=NetworkService,NetworkServiceInProcess',
            ],
            ignore_default_args=['--enable-automation'],  # Remove flag de automação
        )
        
        self.page = await self.context.new_page()
        
        # Anti-detecção AVANÇADA
        await self.page.add_init_script("""
            // =============================================
            // ANTI-DETECÇÃO PARA reCAPTCHA
            // =============================================
            
            // 1. Remove webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // 2. Fake plugins (Chrome real tem plugins)
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
                    ];
                    plugins.item = (i) => plugins[i];
                    plugins.namedItem = (name) => plugins.find(p => p.name === name);
                    plugins.refresh = () => {};
                    return plugins;
                },
            });
            
            // 3. Fake mimeTypes
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => {
                    const mimes = [
                        { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                    ];
                    mimes.item = (i) => mimes[i];
                    mimes.namedItem = (name) => mimes.find(m => m.type === name);
                    return mimes;
                },
            });
            
            // 4. Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en'],
            });
            
            // 5. Chrome object (importante!)
            window.chrome = {
                runtime: {
                    PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' },
                    PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformNaclArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                    RequestUpdateCheckStatus: { THROTTLED: 'throttled', NO_UPDATE: 'no_update', UPDATE_AVAILABLE: 'update_available' },
                    OnInstalledReason: { INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update' },
                    OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
                },
            };
            
            // 6. Permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 7. WebGL Vendor e Renderer (importante para fingerprint)
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';  // UNMASKED_VENDOR_WEBGL
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER_WEBGL
                return getParameter.call(this, parameter);
            };
            
            // 8. Remove Playwright/Selenium traces
            delete window.__playwright;
            delete window.__selenium_unwrapped;
            delete window.__driver_evaluate;
            delete window.__webdriver_evaluate;
            delete window.__driver_unwrapped;
            delete window.__webdriver_unwrapped;
            delete window.__fxdriver_evaluate;
            delete window.__fxdriver_unwrapped;
            delete document.__selenium_unwrapped;
            delete document.__webdriver_evaluate;
            delete document.__driver_evaluate;
            
            // 9. Console.debug
            console.debug = () => {};
            
            // 10. Notification (para parecer browser real)
            if (!window.Notification) {
                window.Notification = {
                    permission: 'default',
                    requestPermission: () => Promise.resolve('default'),
                };
            }
        """)
        
        print("✅ Browser inicializado com anti-detecção avançada")
    
    async def _close_browser(self):
        """Fecha o browser mantendo os dados"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def _human_delay(self, min_ms: int = 500, max_ms: int = 1500):
        """Delay humanizado para evitar detecção"""
        import random
        delay = random.randint(min_ms, max_ms)
        await asyncio.sleep(delay / 1000)
    
    async def _scroll_suave(self, page: Page, vezes: int = 3):
        """Scroll suave para carregar lazy loading"""
        for i in range(vezes):
            await page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
            await self._human_delay(300, 800)
        
        # Volta ao topo
        await page.evaluate('window.scrollTo(0, 0)')
        await self._human_delay(200, 400)
    
    # =========================================
    # LOGIN
    # =========================================
    
    async def verificar_login(self) -> bool:
        """Verifica se está logado como afiliado"""
        try:
            await self.page.goto(self.URL_OFERTAS, wait_until='networkidle', timeout=30000)
            await self._human_delay(1000, 2000)
            
            # Procura elementos que só aparecem quando logado como afiliado
            # Baseado na imagem 2: "Afiliados | Métricas | Configurações"
            afiliado_element = await self.page.query_selector(
                "[class*='affiliate'], [class*='nav-affiliate'], :text('Afiliados'), :text('GANHOS')"
            )
            
            if afiliado_element:
                print("✅ Login de afiliado detectado!")
                return True
            
            # Verifica se tem o nome do usuário no header
            user_element = await self.page.query_selector(
                "[class*='user-name'], [class*='nav-header-user'], :text('Eduardo')"
            )
            
            if user_element:
                print("✅ Usuário logado detectado!")
                return True
            
            print("❌ Não está logado")
            return False
            
        except Exception as e:
            print(f"❌ Erro ao verificar login: {e}")
            return False
    
    async def fazer_login_manual(self):
        """
        Abre o navegador para login manual.
        O usuário faz o login e os cookies são salvos automaticamente.
        """
        print("\n" + "="*60)
        print("🔐 LOGIN MANUAL NECESSÁRIO")
        print("="*60)
        print("1. O navegador vai abrir na página de login")
        print("2. Faça login com sua conta de afiliado")
        print("3. Após logar, volte aqui e pressione ENTER")
        print("="*60 + "\n")
        
        # Abre página de login
        await self.page.goto("https://www.mercadolivre.com.br", wait_until='networkidle')
        await self._human_delay(1000, 2000)
        
        # Clica no botão de entrar
        try:
            login_btn = await self.page.query_selector("a[href*='login'], :text('Entre')")
            if login_btn:
                await login_btn.click()
                await self._human_delay(1000, 2000)
        except:
            pass
        
        # Aguarda o usuário fazer login
        input("\n⏳ Pressione ENTER após fazer login no navegador...")
        
        # Verifica se o login funcionou
        if await self.verificar_login():
            print("✅ Login salvo com sucesso!")
            print("   Os cookies foram armazenados em:", self.USER_DATA_DIR)
            return True
        else:
            print("❌ Login não detectado. Tente novamente.")
            return False
    
    # =========================================
    # SCRAPING DE OFERTAS
    # =========================================
    
    async def obter_links_ofertas(self, url: str = None) -> list[str]:
        """
        Obtém lista de links de produtos da página de ofertas
        
        Returns:
            Lista de URLs dos produtos
        """
        url = url or self.URL_OFERTAS
        
        print(f"\n🔄 Acessando página de ofertas: {url}")
        await self.page.goto(url, wait_until='networkidle', timeout=30000)
        await self._human_delay(1500, 2500)
        
        # Scroll para carregar mais produtos
        await self._scroll_suave(self.page, vezes=5)
        
        # Extrai links de produtos
        links = await self.page.evaluate(f"""
            () => {{
                const links = new Set();
                const anchors = document.querySelectorAll('a[href*="/p/MLB"], a[href*="produto.mercadolivre"]');
                
                anchors.forEach(a => {{
                    const href = a.href;
                    if (href && (href.includes('/p/MLB') || href.includes('produto.mercadolivre'))) {{
                        // Remove parâmetros de tracking
                        const url = href.split('#')[0].split('?')[0];
                        links.add(url);
                    }}
                }});
                
                return Array.from(links).slice(0, {self.max_produtos});
            }}
        """)
        
        print(f"✅ Encontrados {len(links)} produtos")
        return links
    
    async def extrair_dados_produto(self, url: str) -> dict:
        """
        Acessa a página do produto e extrai os dados + link de afiliado
        
        Args:
            url: URL do produto
            
        Returns:
            Dict com dados do produto incluindo link de afiliado
        """
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
            "preco_pix": None,
            "desconto": None,
            "status": "pendente",
            "erro": None
        }
        
        try:
            # Acessa a página do produto
            print(f"  📦 Acessando: {url[:60]}...")
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await self._human_delay(1000, 2000)
            
            # Extrai MLB ID da URL
            mlb_match = re.search(r'MLB[-]?(\d+)', url)
            if mlb_match:
                produto["mlb_id"] = f"MLB{mlb_match.group(1)}"
            
            # Extrai dados básicos via JS
            dados = await self.page.evaluate("""
                () => {
                    const dados = {};
                    
                    // Nome
                    const titulo = document.querySelector('h1.ui-pdp-title, .ui-pdp-title');
                    dados.nome = titulo?.textContent?.trim() || '';
                    
                    // Foto
                    const foto = document.querySelector('.ui-pdp-image, img[data-zoom]');
                    dados.foto = foto?.src || foto?.dataset?.src || '';
                    
                    // Preço atual
                    const precoAtual = document.querySelector('.ui-pdp-price__second-line .andes-money-amount__fraction');
                    dados.preco_atual = precoAtual?.textContent?.trim() || '';
                    
                    // Preço original (riscado)
                    const precoOriginal = document.querySelector('.ui-pdp-price__original-value .andes-money-amount__fraction, s .andes-money-amount__fraction');
                    dados.preco_original = precoOriginal?.textContent?.trim() || '';
                    
                    // Desconto
                    const desconto = document.querySelector('.ui-pdp-price__second-line__label, .andes-money-amount__discount');
                    dados.desconto = desconto?.textContent?.trim() || '';
                    
                    return dados;
                }
            """)
            
            produto["nome"] = dados.get("nome")
            produto["foto_url"] = dados.get("foto")
            produto["preco_atual"] = self._parse_preco(dados.get("preco_atual"))
            produto["preco_original"] = self._parse_preco(dados.get("preco_original"))
            produto["desconto"] = self._parse_desconto(dados.get("desconto"))
            
            # ===================================
            # EXTRAI LINK DE AFILIADO
            # ===================================
            link_afiliado = await self._extrair_link_afiliado()
            
            if link_afiliado:
                produto["url_afiliado"] = link_afiliado.get("url_longa")
                produto["url_curta"] = link_afiliado.get("url_curta")
                produto["product_id"] = link_afiliado.get("product_id")
                produto["status"] = "sucesso"
                print(f"     ✅ Link: {produto['url_curta']}")
            else:
                produto["status"] = "sem_link"
                print(f"     ⚠️ Não conseguiu extrair link de afiliado")
            
        except Exception as e:
            produto["status"] = "erro"
            produto["erro"] = str(e)
            print(f"     ❌ Erro: {e}")
        
        return produto
    
    async def _extrair_link_afiliado(self) -> Optional[dict]:
        """
        Clica em Compartilhar e extrai o link de afiliado do modal
        
        Returns:
            Dict com url_curta, url_longa, product_id ou None se falhar
        """
        try:
            # Procura o botão Compartilhar na barra de afiliados
            # Baseado na imagem: botão azul "Compartilhar" no canto superior direito
            btn_compartilhar = await self.page.wait_for_selector(
                "button:has-text('Compartilhar'), [data-testid*='share'], a:has-text('Compartilhar')",
                timeout=5000
            )
            
            if not btn_compartilhar:
                print("     ⚠️ Botão Compartilhar não encontrado")
                return None
            
            # Clica no botão
            await btn_compartilhar.click()
            await self._human_delay(1000, 2000)

            # Aguarda o modal aparecer - usando múltiplos seletores
            await self.page.wait_for_selector(
                "input[value*='mercadolivre.com/sec'], input[value*='meli.to'], div:has-text('Link do produto')",
                timeout=5000
            )

            await self._human_delay(500, 1000)

            # MÉTODO 1: Tenta extrair usando o XPath específico do modal
            resultado = {}

            try:
                # Usa o XPath fornecido como base para encontrar o input
                xpath_base = "/html/body/div[1]/nav/div/div[3]/div[2]/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div"
                elemento_xpath = await self.page.query_selector(f"xpath={xpath_base}")

                if elemento_xpath:
                    # Procura input dentro desse elemento
                    input_link = await elemento_xpath.query_selector("input[type='text'], input[readonly]")
                    if input_link:
                        url_curta = await input_link.get_attribute("value")
                        if url_curta and ("mercadolivre.com/sec/" in url_curta or "meli.to/" in url_curta):
                            resultado["url_curta"] = url_curta.strip()
                            print(f"     ✅ Link extraído via XPath: {url_curta[:50]}...")
            except Exception as e:
                print(f"     ⚠️ XPath não funcionou: {e}")

            # MÉTODO 2: Busca todos os inputs visíveis com link
            if not resultado.get("url_curta"):
                try:
                    inputs = await self.page.query_selector_all("input[type='text'], input[readonly]")
                    for input_elem in inputs:
                        value = await input_elem.get_attribute("value") or ""
                        if "mercadolivre.com/sec/" in value or "meli.to/" in value:
                            resultado["url_curta"] = value.strip()
                            print(f"     ✅ Link extraído via input: {value[:50]}...")
                            break
                except Exception as e:
                    print(f"     ⚠️ Busca por inputs falhou: {e}")

            # MÉTODO 3: Tenta copiar clicando no botão de copiar
            if not resultado.get("url_curta"):
                try:
                    # Procura botão de copiar
                    btn_copiar = await self.page.query_selector(
                        "button:has-text('Copiar'), button[aria-label*='Copiar'], [class*='copy'] button"
                    )

                    if btn_copiar:
                        # Clica para copiar
                        await btn_copiar.click()
                        await self._human_delay(300, 600)

                        # Tenta ler do clipboard via JS
                        clipboard_text = await self.page.evaluate("""
                            async () => {
                                try {
                                    const text = await navigator.clipboard.readText();
                                    return text;
                                } catch {
                                    return null;
                                }
                            }
                        """)

                        if clipboard_text and ("mercadolivre.com/sec/" in clipboard_text or "meli.to/" in clipboard_text):
                            resultado["url_curta"] = clipboard_text.strip()
                            print(f"     ✅ Link copiado do clipboard: {clipboard_text[:50]}...")
                except Exception as e:
                    print(f"     ⚠️ Método clipboard falhou: {e}")

            # MÉTODO 4: Busca via JavaScript (fallback)
            if not resultado.get("url_curta"):
                try:
                    js_resultado = await self.page.evaluate("""
                        () => {
                            // Procura em todos os elementos de texto
                            const allElements = document.querySelectorAll('*');
                            for (const el of allElements) {
                                const text = el.textContent || el.innerText || el.value || '';
                                if (text.includes('mercadolivre.com/sec/') || text.includes('meli.to/')) {
                                    // Extrai URL
                                    const match = text.match(/(https?:\\/\\/[\\w.-]+\\/sec\\/[\\w-]+)|(https?:\\/\\/meli\\.to\\/[\\w-]+)/);
                                    if (match) {
                                        return match[0];
                                    }
                                }
                            }
                            return null;
                        }
                    """)

                    if js_resultado:
                        resultado["url_curta"] = js_resultado.strip()
                        print(f"     ✅ Link extraído via JS: {js_resultado[:50]}...")
                except Exception as e:
                    print(f"     ⚠️ Busca via JS falhou: {e}")

            # Extrai ID do produto se possível
            try:
                id_inputs = await self.page.query_selector_all("input[value*='-']")
                for input_elem in id_inputs:
                    value = await input_elem.get_attribute("value") or ""
                    if re.match(r'^[A-Z0-9]{6,}-[A-Z0-9]{4,}$', value):
                        resultado["product_id"] = value
                        break
            except:
                pass

            # Fecha o modal
            try:
                close_btn = await self.page.query_selector(
                    "[class*='close'], button[aria-label='Fechar'], [class*='modal'] button, button:has-text('Fechar')"
                )
                if close_btn:
                    await close_btn.click()
                else:
                    await self.page.keyboard.press('Escape')
            except:
                await self.page.keyboard.press('Escape')

            await self._human_delay(300, 600)

            if resultado.get("url_curta"):
                return resultado

            print("     ⚠️ Nenhum método conseguiu extrair o link")
            return None
            
        except Exception as e:
            print(f"     ⚠️ Erro ao extrair link: {e}")
            # Tenta fechar modal se abriu
            try:
                await self.page.keyboard.press('Escape')
            except:
                pass
            return None
    
    def _parse_preco(self, valor: str) -> Optional[float]:
        """Converte string de preço para float"""
        if not valor:
            return None
        try:
            # Remove pontos de milhar e troca vírgula por ponto
            valor = valor.replace('.', '').replace(',', '.').strip()
            return float(re.sub(r'[^\d.]', '', valor))
        except:
            return None
    
    def _parse_desconto(self, valor: str) -> Optional[int]:
        """Extrai porcentagem de desconto"""
        if not valor:
            return None
        try:
            match = re.search(r'(\d+)\s*%', valor)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    # =========================================
    # MÉTODO PRINCIPAL
    # =========================================
    
    async def scrape_ofertas(self, url: str = None, max_produtos: int = None) -> list[dict]:
        """
        Executa o scraping completo das ofertas
        
        Args:
            url: URL da página de ofertas (padrão: ofertas gerais)
            max_produtos: Limite de produtos (padrão: self.max_produtos)
            
        Returns:
            Lista de produtos com links de afiliado
        """
        max_produtos = max_produtos or self.max_produtos
        
        # Verifica login
        if not await self.verificar_login():
            print("\n⚠️ Você precisa fazer login primeiro!")
            logou = await self.fazer_login_manual()
            if not logou:
                return []
        
        # Obtém lista de links
        links = await self.obter_links_ofertas(url)
        links = links[:max_produtos]
        
        print(f"\n🚀 Iniciando extração de {len(links)} produtos...")
        print("="*60)
        
        produtos = []
        for i, link in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}]")
            produto = await self.extrair_dados_produto(link)
            produtos.append(produto)
            
            # Delay entre produtos para evitar rate limit
            if i < len(links):
                await self._human_delay(1500, 3000)
        
        # Resumo
        sucesso = sum(1 for p in produtos if p["status"] == "sucesso")
        falha = len(produtos) - sucesso
        
        print("\n" + "="*60)
        print(f"✅ Concluído: {sucesso} com link | ❌ {falha} sem link")
        print("="*60)
        
        return produtos
    
    async def salvar_resultados(self, produtos: list[dict], arquivo: str = None):
        """Salva resultados em JSON"""
        arquivo = arquivo or f"ofertas_ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(produtos, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Resultados salvos em: {arquivo}")
        return arquivo


# =========================================
# EXECUÇÃO
# =========================================

async def main():
    """Exemplo de uso"""
    
    print("\n" + "="*60)
    print("🛒 SCRAPER MERCADO LIVRE AFILIADO")
    print("="*60)
    
    # headless=False para ver o navegador (necessário para login manual)
    async with ScraperMLAfiliado(
        headless=False,
        wait_ms=1500,
        max_produtos=50,
        etiqueta="egnofertas"
    ) as scraper:
        
        # Executa scraping
        produtos = await scraper.scrape_ofertas()
        
        # Salva resultados
        if produtos:
            await scraper.salvar_resultados(produtos)
            
            # Mostra amostra
            print("\n📋 Amostra dos resultados:")
            for p in produtos[:3]:
                print(f"\n  • {p['nome'][:50] if p['nome'] else 'N/A'}...")
                print(f"    Preço: R$ {p['preco_atual']}")
                print(f"    Link: {p['url_curta']}")


if __name__ == "__main__":
    asyncio.run(main())
