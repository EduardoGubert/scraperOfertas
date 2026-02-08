"""
API REST - Scraper ML Afiliado
Endpoints para scraping de ofertas do Mercado Livre com links de afiliado.

Endpoints:
- GET  /health           - Health check basico
- GET  /auth/status      - Verifica se cookies estao validos (NAO inicia browser)
- GET  /auth/check       - Testa login abrindo browser (mais lento, mais preciso)
- POST /scrape/ofertas   - Executa scraping com links de afiliado
"""

import os
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from scraper_ml_afiliado import ScraperMLAfiliado


# ============================================
# CONFIGURACAO
# ============================================
API_KEY = os.getenv("SCRAPER_API_KEY", "egn-2025-secret-key")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Detecta se esta rodando em Docker ou localmente
if os.path.exists("/app"):
    BROWSER_DATA_DIR = "/app/ml_browser_data"
else:
    BROWSER_DATA_DIR = os.path.join(os.path.dirname(__file__), "ml_browser_data")

METADATA_FILE = os.path.join(BROWSER_DATA_DIR, "login_metadata.json")


# Estado global
scraper_instance: Optional[ScraperMLAfiliado] = None


def get_proxy_config() -> Optional[dict]:
    """Le configuracao de proxy das variaveis de ambiente"""
    proxy_server = os.getenv('PROXY_SERVER')
    
    if not proxy_server:
        return None
    
    proxy_config = {'server': proxy_server}
    
    proxy_user = os.getenv('PROXY_USER')
    proxy_pass = os.getenv('PROXY_PASS')
    
    if proxy_user:
        proxy_config['username'] = proxy_user
    if proxy_pass:
        proxy_config['password'] = proxy_pass
    
    print(f"🌐 Proxy configurado: {proxy_server}")
    return proxy_config


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verifica API Key"""
    if api_key is None:
        raise HTTPException(status_code=401, detail="API Key nao fornecida. Use header X-API-Key")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="API Key invalida")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicacao"""
    global scraper_instance
    print("Iniciando API do Scraper ML Afiliado...")
    yield
    if scraper_instance:
        await scraper_instance._close_browser()
    print("API encerrada")


# ============================================
# APP FASTAPI
# ============================================
app = FastAPI(
    title="Scraper ML Afiliado API",
    description="""
API para scraping de ofertas do Mercado Livre com links de afiliado.

## Fluxo de uso:
1. Faca login localmente: `python login_local.py`
2. Sincronize cookies para VPS: `./sync_to_vps.ps1`
3. Verifique status: `GET /auth/status`
4. Execute scraping: `POST /scrape/ofertas`
    """,
    version="3.0.0",
    lifespan=lifespan
)


# ============================================
# MODELS
# ============================================
class ScrapeRequest(BaseModel):
    url: Optional[str] = None
    max_produtos: Optional[int] = 20
    headless: Optional[bool] = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_produtos": 20,
                "headless": True
            }
        }
    )


class AuthStatusResponse(BaseModel):
    cookies_exist: bool
    cookies_valid: bool
    login_date: Optional[str] = None
    days_since_login: Optional[int] = None
    days_until_expiry: Optional[int] = None
    message: str
    action_required: Optional[str] = None


class ScrapeResponse(BaseModel):
    success: bool
    total: int
    total_com_link: int
    total_sem_link: int
    produtos: list[dict]
    scraped_at: str


# ============================================
# FUNCOES AUXILIARES
# ============================================
def check_cookies_files() -> dict:
    """
    Verifica se os arquivos de cookies existem.
    NAO abre o browser, apenas checa arquivos.
    """
    result = {
        "cookies_exist": False,
        "metadata_exist": False,
        "login_date": None,
        "days_since_login": None,
        "days_until_expiry": None,
    }

    # Verifica se diretorio existe
    if not os.path.exists(BROWSER_DATA_DIR):
        return result

    # Verifica arquivos importantes do Chromium
    required_files = ["Default/Cookies", "Default/Network/Cookies"]
    for file in required_files:
        full_path = os.path.join(BROWSER_DATA_DIR, file)
        if os.path.exists(full_path):
            result["cookies_exist"] = True
            break

    # Verifica metadata de login
    if os.path.exists(METADATA_FILE):
        result["metadata_exist"] = True
        try:
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)

            login_date = datetime.fromisoformat(metadata.get("login_date", ""))
            expires_date = datetime.fromisoformat(metadata.get("expires_estimate", ""))

            result["login_date"] = login_date.strftime("%Y-%m-%d %H:%M")
            result["days_since_login"] = (datetime.now() - login_date).days
            result["days_until_expiry"] = (expires_date - datetime.now()).days

        except Exception:
            pass

    return result


# ============================================
# ENDPOINTS
# ============================================
@app.get("/")
async def root():
    """Pagina inicial com documentacao dos endpoints"""
    return {
        "api": "Scraper ML Afiliado",
        "version": "3.0.0",
        "endpoints": {
            "GET /health": "Health check basico",
            "GET /auth/status": "Verifica cookies (rapido, sem browser)",
            "GET /auth/check": "Testa login real (lento, abre browser)",
            "POST /scrape/ofertas": "Executa scraping"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check basico"""
    cookies_info = check_cookies_files()
    return {
        "status": "healthy",
        "cookies_exist": cookies_info["cookies_exist"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/auth/status", response_model=AuthStatusResponse)
async def auth_status(api_key: str = Depends(verify_api_key)):
    """
    Verifica status dos cookies de autenticacao.

    Este endpoint e RAPIDO pois NAO abre o browser.
    Apenas verifica se os arquivos de cookies existem e se estao dentro da validade.

    Para verificacao completa (abre browser e testa login real), use GET /auth/check
    """
    cookies_info = check_cookies_files()

    # Sem cookies
    if not cookies_info["cookies_exist"]:
        return AuthStatusResponse(
            cookies_exist=False,
            cookies_valid=False,
            message="Cookies nao encontrados. Login necessario.",
            action_required="Execute localmente: python login_local.py && ./sync_to_vps.ps1"
        )

    # Com cookies mas sem metadata
    if not cookies_info.get("metadata_exist"):
        return AuthStatusResponse(
            cookies_exist=True,
            cookies_valid=False,
            login_date=None,
            message="Cookies existem mas sem metadata. Validade desconhecida.",
            action_required="Recomendado refazer login para ter controle de validade"
        )

    # Com cookies e metadata
    days_until_expiry = cookies_info.get("days_until_expiry", 0)

    if days_until_expiry <= 0:
        return AuthStatusResponse(
            cookies_exist=True,
            cookies_valid=False,
            login_date=cookies_info.get("login_date"),
            days_since_login=cookies_info.get("days_since_login"),
            days_until_expiry=days_until_expiry,
            message="Cookies EXPIRADOS!",
            action_required="Execute localmente: python login_local.py && ./sync_to_vps.ps1"
        )

    if days_until_expiry <= 2:
        return AuthStatusResponse(
            cookies_exist=True,
            cookies_valid=True,
            login_date=cookies_info.get("login_date"),
            days_since_login=cookies_info.get("days_since_login"),
            days_until_expiry=days_until_expiry,
            message=f"Cookies validos mas EXPIRANDO EM {days_until_expiry} DIAS!",
            action_required="Recomendado refazer login em breve"
        )

    return AuthStatusResponse(
        cookies_exist=True,
        cookies_valid=True,
        login_date=cookies_info.get("login_date"),
        days_since_login=cookies_info.get("days_since_login"),
        days_until_expiry=days_until_expiry,
        message=f"Cookies validos. Expiram em {days_until_expiry} dias."
    )


@app.get("/auth/check")
async def auth_check(api_key: str = Depends(verify_api_key)):
    """
    Verifica login REAL abrindo o browser e testando no site.

    ATENCAO: Este endpoint e LENTO (5-15 segundos) pois abre o browser.
    Use GET /auth/status para verificacao rapida.

    Este endpoint e util para confirmar que os cookies realmente funcionam
    antes de executar um scraping grande.
    """
    global scraper_instance

    try:
        # Fecha instancia anterior se existir
        if scraper_instance:
            try:
                await scraper_instance._close_browser()
            except:
                pass
            scraper_instance = None

        # Cria nova instancia
        scraper_instance = ScraperMLAfiliado(
            headless=True,
            wait_ms=1500,
            max_produtos=1,
            user_data_dir=BROWSER_DATA_DIR,
            proxy=get_proxy_config(),
            use_chrome=True  # Tenta usar Chrome real (auto-detecta se disponível)
        )
        await scraper_instance._init_browser()

        # Verifica login
        is_logged_in = await scraper_instance.verificar_login()

        # Fecha browser apos verificacao
        await scraper_instance._close_browser()
        scraper_instance = None

        if is_logged_in:
            return {
                "logged_in": True,
                "message": "Login de afiliado confirmado! Pronto para scraping.",
                "checked_at": datetime.now().isoformat()
            }
        else:
            return JSONResponse(
                status_code=401,
                content={
                    "logged_in": False,
                    "message": "NAO esta logado como afiliado!",
                    "action_required": "Execute localmente: python login_local.py && ./sync_to_vps.ps1",
                    "checked_at": datetime.now().isoformat()
                }
            )

    except Exception as e:
        # Garante que browser seja fechado em caso de erro
        if scraper_instance:
            try:
                await scraper_instance._close_browser()
            except:
                pass
            scraper_instance = None

        return JSONResponse(
            status_code=500,
            content={
                "logged_in": False,
                "error": str(e),
                "message": "Erro ao verificar login",
                "checked_at": datetime.now().isoformat()
            }
        )


@app.post("/scrape/ofertas", response_model=ScrapeResponse)
async def scrape_ofertas(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """
    Executa scraping das ofertas do ML com links de afiliado.

    Requer que os cookies de login estejam configurados.
    Verifique com GET /auth/status antes de executar.
    """
    global scraper_instance

    try:
        # Fecha instancia anterior se existir (evita conflito de sessao)
        if scraper_instance:
            try:
                await scraper_instance._close_browser()
            except:
                pass
            scraper_instance = None

        # Verifica cookies primeiro (rapido)
        cookies_info = check_cookies_files()
        if not cookies_info["cookies_exist"]:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Cookies nao encontrados",
                    "action": "Execute localmente: python login_local.py && ./sync_to_vps.ps1"
                }
            )

        # Inicializa scraper
        scraper_instance = ScraperMLAfiliado(
            headless=request.headless,
            wait_ms=1500,
            max_produtos=request.max_produtos,
            user_data_dir=BROWSER_DATA_DIR,
            proxy=get_proxy_config(),
            use_chrome=True  # Tenta usar Chrome real (auto-detecta se disponível)
        )
        await scraper_instance._init_browser()

        # Verifica login real
        is_logged_in = await scraper_instance.verificar_login()

        if not is_logged_in:
            await scraper_instance._close_browser()
            scraper_instance = None
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Nao esta logado como afiliado",
                    "action": "Execute localmente: python login_local.py && ./sync_to_vps.ps1"
                }
            )

        # Executa scraping
        produtos = await scraper_instance.scrape_ofertas(
            url=request.url,
            max_produtos=request.max_produtos
        )

        # Fecha browser apos scraping
        await scraper_instance._close_browser()
        scraper_instance = None

        # Calcula estatisticas
        total_com_link = sum(1 for p in produtos if p.get("url_curta"))
        total_sem_link = len(produtos) - total_com_link

        return ScrapeResponse(
            success=True,
            total=len(produtos),
            total_com_link=total_com_link,
            total_sem_link=total_sem_link,
            produtos=produtos,
            scraped_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        # Garante que browser seja fechado
        if scraper_instance:
            try:
                await scraper_instance._close_browser()
            except:
                pass
            scraper_instance = None
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/ofertas/relampago", response_model=ScrapeResponse)
async def scrape_ofertas_relampago(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scraping especifico para ofertas relampago"""
    request.url = "https://www.mercadolivre.com.br/ofertas#deal_type=lightning"
    return await scrape_ofertas(request, api_key)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
