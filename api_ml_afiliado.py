"""
API REST para Scraper ML Afiliado
Integração com n8n, Make, Zapier

Endpoints:
- POST /login - Inicia sessão de login manual
- GET /login/status - Verifica se está logado
- POST /scrape/ofertas - Scraping completo com links de afiliado
- GET /health - Health check
"""

import asyncio
import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from scraper_ml_afiliado import ScraperMLAfiliado


# ============================================
# CONFIGURAÇÃO
# ============================================
API_KEY = os.getenv("SCRAPER_API_KEY", "egn-2025-secret-key")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Estado global do scraper
scraper_instance: Optional[ScraperMLAfiliado] = None
is_logged_in: bool = False


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verifica API Key"""
    if api_key is None:
        raise HTTPException(status_code=401, detail="API Key não fornecida")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="API Key inválida")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicação"""
    global scraper_instance
    print("🚀 Iniciando API do Scraper ML Afiliado...")
    yield
    # Cleanup
    if scraper_instance:
        await scraper_instance._close_browser()
    print("👋 API encerrada")


# ============================================
# APP FASTAPI
# ============================================
app = FastAPI(
    title="Scraper ML Afiliado API",
    description="API para scraping de ofertas do Mercado Livre com links de afiliado",
    version="2.0.0",
    lifespan=lifespan
)


# ============================================
# MODELS
# ============================================
class ScrapeRequest(BaseModel):
    url: Optional[str] = None  # URL das ofertas (padrão: /ofertas)
    max_produtos: Optional[int] = 50
    headless: Optional[bool] = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.mercadolivre.com.br/ofertas",
                "max_produtos": 50,
                "headless": True
            }
        }


class Produto(BaseModel):
    url_original: str
    url_afiliado: Optional[str]
    url_curta: Optional[str]
    product_id: Optional[str]
    mlb_id: Optional[str]
    nome: Optional[str]
    foto_url: Optional[str]
    preco_original: Optional[float]
    preco_atual: Optional[float]
    preco_pix: Optional[float]
    desconto: Optional[int]
    status: str
    erro: Optional[str]


class ScrapeResponse(BaseModel):
    success: bool
    total: int
    total_com_link: int
    total_sem_link: int
    produtos: list[dict]
    scraped_at: str
    source: str


class LoginStatusResponse(BaseModel):
    logged_in: bool
    message: str


# ============================================
# ENDPOINTS PÚBLICOS
# ============================================
@app.get("/")
async def root():
    return {
        "message": "Scraper ML Afiliado API",
        "version": "2.0.0",
        "endpoints": {
            "GET /health": "Health check",
            "GET /login/status": "Verifica status do login",
            "POST /login/init": "Inicia browser para login manual",
            "POST /scrape/ofertas": "Scraping com links de afiliado",
        }
    }


@app.get("/health")
async def health():
    global is_logged_in
    return {
        "status": "healthy",
        "logged_in": is_logged_in,
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# ENDPOINTS DE LOGIN
# ============================================
@app.get("/login/status", response_model=LoginStatusResponse)
async def login_status(api_key: str = Depends(verify_api_key)):
    """Verifica se o scraper está logado"""
    global scraper_instance, is_logged_in
    
    if not scraper_instance:
        return LoginStatusResponse(
            logged_in=False,
            message="Scraper não inicializado. Use POST /login/init primeiro."
        )
    
    try:
        is_logged_in = await scraper_instance.verificar_login()
        return LoginStatusResponse(
            logged_in=is_logged_in,
            message="Logado como afiliado" if is_logged_in else "Não está logado"
        )
    except Exception as e:
        return LoginStatusResponse(
            logged_in=False,
            message=f"Erro ao verificar: {str(e)}"
        )


@app.post("/login/init")
async def login_init(api_key: str = Depends(verify_api_key)):
    """
    Inicializa o browser para login manual.

    ⚠️ ATENÇÃO: Funciona apenas localmente (não funciona na VPS sem X server)

    Para fazer login na VPS:
    1. Execute localmente: python login_manual.py
    2. Sincronize cookies: ./sync_to_vps.ps1
    """
    global scraper_instance, is_logged_in

    # Detecta se está rodando em ambiente sem display (VPS)
    if not os.environ.get("DISPLAY"):
        raise HTTPException(
            status_code=501,
            detail={
                "error": "Login visual não suportado na VPS (sem X server)",
                "solution": [
                    "1. Execute localmente: python login_manual.py",
                    "2. Sincronize cookies: ./sync_to_vps.ps1"
                ]
            }
        )

    try:
        # Fecha instância anterior se existir
        if scraper_instance:
            await scraper_instance._close_browser()

        # Cria nova instância com headless=False
        scraper_instance = ScraperMLAfiliado(
            headless=False,  # Precisa ver o navegador
            wait_ms=1500,
            max_produtos=50
        )
        await scraper_instance._init_browser()

        # Navega para a página inicial
        await scraper_instance.page.goto("https://www.mercadolivre.com.br")

        return {
            "success": True,
            "message": "Browser iniciado. Faça login manualmente.",
            "next_step": "Após fazer login, chame GET /login/status para verificar"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS DE SCRAPING
# ============================================
@app.post("/scrape/ofertas", response_model=ScrapeResponse)
async def scrape_ofertas(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """
    Executa scraping das ofertas do ML com links de afiliado.
    
    Requer que o login tenha sido feito previamente.
    """
    global scraper_instance, is_logged_in
    
    try:
        # Inicializa scraper se necessário
        if not scraper_instance:
            scraper_instance = ScraperMLAfiliado(
                headless=request.headless,
                wait_ms=1500,
                max_produtos=request.max_produtos
            )
            await scraper_instance._init_browser()
        
        # Verifica login
        is_logged_in = await scraper_instance.verificar_login()
        
        if not is_logged_in:
            raise HTTPException(
                status_code=401,
                detail="Não está logado. Use POST /login/init e faça login manual primeiro."
            )
        
        # Executa scraping
        produtos = await scraper_instance.scrape_ofertas(
            url=request.url,
            max_produtos=request.max_produtos
        )
        
        # Calcula estatísticas
        total_com_link = sum(1 for p in produtos if p.get("url_curta"))
        total_sem_link = len(produtos) - total_com_link
        
        return ScrapeResponse(
            success=True,
            total=len(produtos),
            total_com_link=total_com_link,
            total_sem_link=total_sem_link,
            produtos=produtos,
            scraped_at=datetime.now().isoformat(),
            source=request.url or "https://www.mercadolivre.com.br/ofertas"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/ofertas/relampago", response_model=ScrapeResponse)
async def scrape_ofertas_relampago(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scraping específico para ofertas relâmpago"""
    request.url = "https://www.mercadolivre.com.br/ofertas#deal_type=lightning"
    return await scrape_ofertas(request, api_key)


# ============================================
# ENDPOINT PARA n8n (WEBHOOK SIMPLIFICADO)
# ============================================
@app.post("/webhook/scrape")
async def webhook_scrape(
    max_produtos: int = 50,
    api_key: str = Depends(verify_api_key)
):
    """
    Endpoint simplificado para n8n/webhooks.
    Retorna apenas os produtos com link de afiliado válido.
    """
    global scraper_instance, is_logged_in
    
    try:
        if not scraper_instance:
            scraper_instance = ScraperMLAfiliado(
                headless=True,
                max_produtos=max_produtos
            )
            await scraper_instance._init_browser()
        
        is_logged_in = await scraper_instance.verificar_login()
        
        if not is_logged_in:
            return JSONResponse(
                status_code=401,
                content={"error": "Não está logado", "action": "Faça login em POST /login/init"}
            )
        
        produtos = await scraper_instance.scrape_ofertas(max_produtos=max_produtos)
        
        # Filtra apenas produtos com link válido
        produtos_validos = [
            {
                "nome": p["nome"],
                "preco": p["preco_atual"],
                "preco_original": p["preco_original"],
                "desconto": p["desconto"],
                "foto": p["foto_url"],
                "link": p["url_curta"],
                "mlb_id": p["mlb_id"]
            }
            for p in produtos
            if p.get("url_curta")
        ]
        
        return {
            "success": True,
            "total": len(produtos_validos),
            "produtos": produtos_validos,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
