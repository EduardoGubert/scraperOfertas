from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

from src.application.use_cases.run_all_jobs import run_jobs_in_sequence
from src.bootstrap import build_container
from src.infrastructure.config.settings import get_settings


settings = get_settings()
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

BROWSER_DATA_DIR = settings.browser_data_dir
METADATA_FILE = os.path.join(BROWSER_DATA_DIR, "login_metadata.json")


class ScrapeRequest(BaseModel):
    url: Optional[str] = None
    max_produtos: Optional[int] = settings.scraper_max_produtos_default
    headless: Optional[bool] = settings.scraper_headless

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_produtos": settings.scraper_max_produtos_default,
                "headless": settings.scraper_headless,
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


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key is None:
        raise HTTPException(status_code=401, detail="API Key nao fornecida. Use header X-API-Key")
    if api_key != settings.scraper_api_key:
        raise HTTPException(status_code=403, detail="API Key invalida")
    return api_key


def check_cookies_files() -> dict:
    result = {
        "cookies_exist": False,
        "metadata_exist": False,
        "login_date": None,
        "days_since_login": None,
        "days_until_expiry": None,
    }
    if not os.path.exists(BROWSER_DATA_DIR):
        return result

    required_files = ["Default/Cookies", "Default/Network/Cookies"]
    for file in required_files:
        if os.path.exists(os.path.join(BROWSER_DATA_DIR, file)):
            result["cookies_exist"] = True
            break

    if os.path.exists(METADATA_FILE):
        result["metadata_exist"] = True
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as file:
                metadata = json.load(file)
            login_date = datetime.fromisoformat(metadata.get("login_date", ""))
            expires_date = datetime.fromisoformat(metadata.get("expires_estimate", ""))

            result["login_date"] = login_date.strftime("%Y-%m-%d %H:%M")
            result["days_since_login"] = (datetime.now() - login_date).days
            result["days_until_expiry"] = (expires_date - datetime.now()).days
        except Exception:
            pass
    return result


app = FastAPI(
    title="Scraper ML Afiliado API",
    description="API para scraping de ofertas, ofertas relampago e cupons com persistencia no PostgreSQL.",
    version="4.0.0",
)


@app.get("/")
async def root():
    return {
        "api": "Scraper ML Afiliado",
        "version": "4.0.0",
        "endpoints": {
            "GET /health": "Health check",
            "GET /auth/status": "Status de cookies",
            "GET /auth/check": "Verificacao real de login",
            "POST /scrape/ofertas": "Scraper ofertas",
            "POST /scrape/ofertas/relampago": "Scraper ofertas relampago",
            "POST /scrape/cupons": "Scraper cupons",
            "POST /scrape/todos": "Executa ofertas -> relampago -> cupons",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    cookies_info = check_cookies_files()
    return {
        "status": "healthy",
        "cookies_exist": cookies_info["cookies_exist"],
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/auth/status", response_model=AuthStatusResponse)
async def auth_status(api_key: str = Depends(verify_api_key)):
    cookies_info = check_cookies_files()
    if not cookies_info["cookies_exist"]:
        return AuthStatusResponse(
            cookies_exist=False,
            cookies_valid=False,
            message="Cookies nao encontrados. Login necessario.",
            action_required="Execute localmente: python login_local.py && ./sync_to_vps.ps1",
        )

    if not cookies_info.get("metadata_exist"):
        return AuthStatusResponse(
            cookies_exist=True,
            cookies_valid=False,
            login_date=None,
            message="Cookies existem mas sem metadata. Validade desconhecida.",
            action_required="Recomendado refazer login para ter controle de validade",
        )

    days_until_expiry = cookies_info.get("days_until_expiry", 0)
    if days_until_expiry <= 0:
        return AuthStatusResponse(
            cookies_exist=True,
            cookies_valid=False,
            login_date=cookies_info.get("login_date"),
            days_since_login=cookies_info.get("days_since_login"),
            days_until_expiry=days_until_expiry,
            message="Cookies expirados",
            action_required="Execute localmente: python login_local.py && ./sync_to_vps.ps1",
        )

    return AuthStatusResponse(
        cookies_exist=True,
        cookies_valid=True,
        login_date=cookies_info.get("login_date"),
        days_since_login=cookies_info.get("days_since_login"),
        days_until_expiry=days_until_expiry,
        message=f"Cookies validos. Expiram em {days_until_expiry} dias.",
    )


@app.get("/auth/check")
async def auth_check(api_key: str = Depends(verify_api_key)):
    try:
        async with build_container(settings) as container:
            async with container.engine_factory(headless=True, max_produtos=1) as engine:
                is_logged_in = await engine.verificar_login()
        if is_logged_in:
            return {
                "logged_in": True,
                "message": "Login de afiliado confirmado.",
                "checked_at": datetime.now().isoformat(),
            }
        return JSONResponse(
            status_code=401,
            content={
                "logged_in": False,
                "message": "Nao esta logado como afiliado",
                "action_required": "Execute localmente: python login_local.py && ./sync_to_vps.ps1",
                "checked_at": datetime.now().isoformat(),
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "logged_in": False,
                "message": "Erro ao verificar login",
                "error": str(exc),
                "checked_at": datetime.now().isoformat(),
            },
        )


async def _run_single_scraper(scraper_type: str, request: ScrapeRequest) -> ScrapeResponse:
    max_items = request.max_produtos or settings.scraper_max_produtos_default
    headless = settings.scraper_headless if request.headless is None else request.headless

    async with build_container(settings) as container:
        async with container.engine_factory(headless=headless, max_produtos=max_items) as engine:
            if not await engine.verificar_login():
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "Nao esta logado como afiliado",
                        "action": "Execute localmente: python login_local.py && ./sync_to_vps.ps1",
                    },
                )
            start_url = request.url if scraper_type in {"ofertas", "ofertas_relampago"} else None
            result = await container.job_use_case.execute(
                scraper_type=scraper_type,
                max_items=max_items,
                engine=engine,
                start_url=start_url,
            )

    total_com_link = sum(1 for item in result.itens if item.get("url_curta"))
    total = len(result.itens)
    return ScrapeResponse(
        success=True,
        total=total,
        total_com_link=total_com_link,
        total_sem_link=total - total_com_link,
        produtos=result.itens,
        scraped_at=datetime.now().isoformat(),
    )


@app.post("/scrape/ofertas", response_model=ScrapeResponse)
async def scrape_ofertas(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    return await _run_single_scraper("ofertas", request)


@app.post("/scrape/ofertas/relampago", response_model=ScrapeResponse)
async def scrape_ofertas_relampago(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    return await _run_single_scraper("ofertas_relampago", request)


@app.post("/scrape/cupons", response_model=ScrapeResponse)
async def scrape_cupons(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    return await _run_single_scraper("cupons", request)


@app.post("/scrape/todos")
async def scrape_todos(request: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    max_items = request.max_produtos or settings.scraper_max_produtos_default
    headless = settings.scraper_headless if request.headless is None else request.headless

    async with build_container(settings) as container:
        results = await run_jobs_in_sequence(
            job_use_case=container.job_use_case,
            engine_factory=lambda: container.engine_factory(headless=headless, max_produtos=max_items),
            max_items=max_items,
            timeout_seconds=settings.scheduler_job_timeout_seconds,
        )

    return {
        "success": True,
        "executado_em": datetime.now().isoformat(),
        "jobs": {
            "ofertas": results.ofertas.__dict__,
            "ofertas_relampago": results.ofertas_relampago.__dict__,
            "cupons": results.cupons.__dict__,
        },
    }
