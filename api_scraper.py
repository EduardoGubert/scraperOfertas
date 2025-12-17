"""
API REST para Scraper de Ofertas
Integração fácil com n8n, Make, Zapier, etc.

Executar: uvicorn api_scraper:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional
import asyncio
import json
from datetime import datetime
from scraper_ofertas import ScraperOfertas

app = FastAPI(
    title="Scraper Ofertas API",
    description="API para scraping de e-commerces brasileiros",
    version="1.0.0"
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


@app.get("/")
async def root():
    return {
        "message": "Scraper Ofertas API",
        "docs": "/docs",
        "endpoints": {
            "POST /scrape": "Faz scraping de uma URL",
            "POST /scrape/magazine": "Scrape Magazine Você/Magalu",
            "POST /scrape/mercadolivre": "Scrape Mercado Livre",
            "POST /scrape/shopee": "Scrape Shopee",
            "POST /scrape/amazon": "Scrape Amazon"
        }
    }


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_auto(request: ScrapeRequest):
    """
    Scraping automático - detecta o site e usa o scraper correto
    
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
async def scrape_magazine(request: ScrapeRequest):
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
async def scrape_ml(request: ScrapeRequest):
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
async def scrape_shopee(request: ScrapeRequest):
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
async def scrape_amazon(request: ScrapeRequest):
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


# Health check para Docker/Kubernetes
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
