"""
API REST para Scraper de Ofertas e Cupons
Integração fácil com n8n, Make, Zapier, etc.

Executar: uvicorn api_scraper:app --host 0.0.0.0 --port 8000
"""

import os
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
from datetime import datetime
from scraper_ofertas import ScraperOfertas

# ============================================
# CONFIGURAÇÃO
# ============================================
API_KEY = os.getenv("SCRAPER_API_KEY", "egn-ofertas-2024-secret-key")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Configuração de afiliados (via variáveis de ambiente)
AFFILIATE_CONFIG = {
    "mercadolivre": {
        "params": {
            "matt_tool": os.getenv("ML_MATT_TOOL", "39349855"),
            "matt_word": os.getenv("ML_MATT_WORD", "egnofertas")
        }
    },
    "magazinevoce": {
        "showcase": os.getenv("MAGALU_SHOWCASE", "magazinegubert")
    }
}


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verifica se a API Key é válida"""
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API Key não fornecida. Use o header 'X-API-Key'."
        )
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="API Key inválida."
        )
    return api_key


# ============================================
# APP FASTAPI
# ============================================
app = FastAPI(
    title="Scraper Ofertas API",
    description="API para scraping de e-commerces brasileiros - Produtos e Cupons",
    version="2.0.0"
)


# ============================================
# MODELS
# ============================================
class ScrapeRequest(BaseModel):
    url: str
    wait_ms: Optional[int] = 1500
    headless: Optional[bool] = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.magazinevoce.com.br/magazinegubert/selecao/ofertasdodia/",
                "wait_ms": 1500,
                "headless": True
            }
        }


class CupomRequest(BaseModel):
    showcase: Optional[str] = "magazinegubert"
    wait_ms: Optional[int] = 1500


class Produto(BaseModel):
    foto: str
    nome: str
    preço: str
    url: str


class ProdutoOferta(BaseModel):
    foto: str
    nome: str
    preço: str
    preço_original: Optional[str] = ""
    desconto: Optional[str] = ""
    url: str


class Cupom(BaseModel):
    categoria: str
    desconto: str
    codigo: str
    imagem: str
    tipo: str


class ScrapeResponse(BaseModel):
    success: bool
    total: int
    produtos: list[Produto]
    scraped_at: str
    source_url: str


class OfertasResponse(BaseModel):
    success: bool
    total: int
    produtos: list[ProdutoOferta]
    scraped_at: str
    source: str


class CuponsResponse(BaseModel):
    success: bool
    total: int
    cupons: list[Cupom]
    scraped_at: str
    source: str


# ============================================
# ENDPOINTS PÚBLICOS
# ============================================
@app.get("/")
async def root():
    return {
        "message": "Scraper Ofertas API",
        "version": "2.0.0",
        "auth": "Requer header 'X-API-Key' para endpoints protegidos",
        "docs": "/docs",
        "endpoints": {
            "produtos": {
                "POST /scrape": "Scraping automático (detecta site)",
                "POST /scrape/magazine": "Magazine Você/Magalu",
                "POST /scrape/mercadolivre": "Mercado Livre",
                "POST /scrape/shopee": "Shopee",
                "POST /scrape/amazon": "Amazon Brasil"
            },
            "cupons": {
                "POST /cupons/magazine": "Cupons do Magazine Você",
                "POST /cupons/mercadolivre": "Cupons do Mercado Livre"
            },
            "ofertas": {
                "POST /ofertas/mercadolivre": "Página de ofertas do ML"
            },
            "público": {
                "GET /health": "Health check"
            }
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================
# ENDPOINTS DE CUPONS
# ============================================
@app.post("/cupons/magazine", response_model=CuponsResponse)
async def get_cupons_magazine(request: CupomRequest, api_key: str = Depends(verify_api_key)):
    """
    Busca cupons disponíveis no Magazine Você
    
    Args:
        showcase: ID da sua loja (ex: magazinegubert)
    """
    try:
        async with ScraperOfertas(
            wait_ms=request.wait_ms,
            headless=True,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            cupons = await scraper.scrape_cupons_magazine(request.showcase)
            
        return CuponsResponse(
            success=True,
            total=len(cupons),
            cupons=cupons,
            scraped_at=datetime.now().isoformat(),
            source=f"Magazine Você - {request.showcase}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cupons/mercadolivre", response_model=CuponsResponse)
async def get_cupons_mercadolivre(api_key: str = Depends(verify_api_key)):
    """
    Busca cupons disponíveis no Mercado Livre
    """
    try:
        async with ScraperOfertas(
            wait_ms=2000,
            headless=True,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            cupons = await scraper.scrape_cupons_mercadolivre()
            
        return CuponsResponse(
            success=True,
            total=len(cupons),
            cupons=cupons,
            scraped_at=datetime.now().isoformat(),
            source="Mercado Livre"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS DE OFERTAS
# ============================================
@app.post("/ofertas/mercadolivre", response_model=OfertasResponse)
async def get_ofertas_mercadolivre(api_key: str = Depends(verify_api_key)):
    """
    Busca ofertas da página principal de ofertas do Mercado Livre
    """
    try:
        async with ScraperOfertas(
            wait_ms=2000,
            headless=True,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            produtos = await scraper.scrape_ofertas_mercadolivre()
            
        return OfertasResponse(
            success=True,
            total=len(produtos),
            produtos=produtos,
            scraped_at=datetime.now().isoformat(),
            source="Mercado Livre Ofertas"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS DE PRODUTOS (mantidos da v1)
# ============================================
@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_auto(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scraping automático - detecta o site e usa o scraper correto"""
    try:
        async with ScraperOfertas(
            wait_ms=request.wait_ms, 
            headless=request.headless,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            produtos = await scraper.scrape_auto(request.url)
            
        return ScrapeResponse(
            success=True,
            total=len(produtos),
            produtos=produtos,
            scraped_at=datetime.now().isoformat(),
            source_url=request.url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/magazine", response_model=ScrapeResponse)
async def scrape_magazine(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scrape específico para Magazine Você / Magalu"""
    try:
        async with ScraperOfertas(
            wait_ms=request.wait_ms,
            headless=request.headless,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            produtos = await scraper.scrape_magazine_voce(request.url)
            
        return ScrapeResponse(
            success=True,
            total=len(produtos),
            produtos=produtos,
            scraped_at=datetime.now().isoformat(),
            source_url=request.url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/mercadolivre", response_model=ScrapeResponse)
async def scrape_ml(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scrape específico para Mercado Livre"""
    try:
        async with ScraperOfertas(
            wait_ms=request.wait_ms,
            headless=request.headless,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            produtos = await scraper.scrape_mercado_livre(request.url)
            
        return ScrapeResponse(
            success=True,
            total=len(produtos),
            produtos=produtos,
            scraped_at=datetime.now().isoformat(),
            source_url=request.url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/shopee", response_model=ScrapeResponse)
async def scrape_shopee(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scrape específico para Shopee"""
    try:
        async with ScraperOfertas(
            wait_ms=request.wait_ms,
            headless=request.headless,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            produtos = await scraper.scrape_shopee(request.url)
            
        return ScrapeResponse(
            success=True,
            total=len(produtos),
            produtos=produtos,
            scraped_at=datetime.now().isoformat(),
            source_url=request.url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/amazon", response_model=ScrapeResponse)
async def scrape_amazon(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scrape específico para Amazon Brasil"""
    try:
        async with ScraperOfertas(
            wait_ms=request.wait_ms,
            headless=request.headless,
            affiliate_config=AFFILIATE_CONFIG
        ) as scraper:
            produtos = await scraper.scrape_amazon(request.url)
            
        return ScrapeResponse(
            success=True,
            total=len(produtos),
            produtos=produtos,
            scraped_at=datetime.now().isoformat(),
            source_url=request.url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)