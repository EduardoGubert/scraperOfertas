from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass
class Settings:
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = _as_int(os.getenv("DB_PORT"), 5432)
    db_name: str = os.getenv("DB_NAME", "")
    db_user: str = os.getenv("DB_USER", "")
    db_pass: str = os.getenv("DB_PASS", "")

    scraper_headless: bool = _as_bool(os.getenv("SCRAPER_HEADLESS"), True)
    scraper_wait_ms: int = _as_int(os.getenv("SCRAPER_WAIT_MS"), 1500)
    scraper_api_key: str = os.getenv("SCRAPER_API_KEY", "egn-2025-secret-key")
    scraper_max_produtos_default: int = _as_int(os.getenv("SCRAPER_MAX_PRODUTOS_DEFAULT"), 30)

    cache_backend: str = os.getenv("CACHE_BACKEND", "redis")
    cache_ttl_seconds: int = _as_int(os.getenv("CACHE_TTL_SECONDS"), 86400)
    cache_json_file: str = os.getenv("CACHE_JSON_FILE", "cache_produtos.json")
    cache_key_prefix: str = os.getenv("CACHE_KEY_PREFIX", "scraperofertas")

    redis_host: str = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port: int = _as_int(os.getenv("REDIS_PORT"), 6379)
    redis_db: int = _as_int(os.getenv("REDIS_DB"), 2)
    redis_password: str | None = os.getenv("REDIS_PASSWORD", None)
    redis_ssl: bool = _as_bool(os.getenv("REDIS_SSL"), False)

    timezone: str = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")

    scheduler_interval_minutes: int = _as_int(os.getenv("SCHEDULER_INTERVAL_MINUTES"), 30)
    scheduler_max_produtos: int = _as_int(os.getenv("SCHEDULER_MAX_PRODUTOS"), 30)
    scheduler_job_timeout_seconds: int = _as_int(os.getenv("SCHEDULER_JOB_TIMEOUT_SECONDS"), 30)

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    logs_dir: str = os.getenv("LOGS_DIR", "logs")

    browser_data_dir: str = os.getenv("BROWSER_DATA_DIR", "ml_browser_data")

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_pass}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def logs_path(self) -> Path:
        return Path(self.logs_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
