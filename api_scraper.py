"""
API REST para Scraper de Ofertas
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
# CONFIGURAÇÃO DA API KEY
# ============================================
# Defina via variável de ambiente ou use o valor padrão
# IMPORTANTE: Troque a chave padrão em produção!
API_KEY = os.getenv("SCRAPER_API_KEY", "egn-ofertas-2024-secret-key")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


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
    description="API para scraping de e-commerces brasileiros",
    version="1.1.0"
)


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


class Produto(BaseModel):
    foto: str
    nome: str
    preço: str
    url: str


class ScrapeResponse(BaseModel):
    success: bool
    total: int
    produtos: list[Produto]
    scraped_at: str
    source_url: str


# ============================================
# ENDPOINTS PÚBLICOS (sem autenticação)
# ============================================
@app.get("/")
async def root():
    return {
        "message": "Scraper Ofertas API",
        "version": "1.1.0",
        "auth": "Requer header 'X-API-Key' para endpoints protegidos",
        "docs": "/docs",
        "endpoints": {
            "POST /scrape": "Faz scraping de uma URL (requer API Key)",
            "POST /scrape/magazine": "Scrape Magazine Você/Magalu (requer API Key)",
            "POST /scrape/mercadolivre": "Scrape Mercado Livre (requer API Key)",
            "POST /scrape/shopee": "Scrape Shopee (requer API Key)",
            "POST /scrape/amazon": "Scrape Amazon (requer API Key)",
            "GET /health": "Health check (público)"
        }
    }


@app.get("/health")
async def health():
    """Health check - público para monitoramento"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================
# ENDPOINTS PROTEGIDOS (requer API Key)
# ============================================
@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_auto(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """
    Scraping automático - detecta o site e usa o scraper correto
    
    Requer header: X-API-Key
    
    Suporta:
    - Magazine Você / Magalu
    - Mercado Livre
    - Shopee
    - Amazon Brasil
    """
    try:
        async with ScraperOfertas(
            wait_ms=request.wait_ms, 
            headless=request.headless
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
            headless=request.headless
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
            headless=request.headless
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
            headless=request.headless
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
            headless=request.headless
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