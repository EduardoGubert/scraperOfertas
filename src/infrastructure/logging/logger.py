from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from src.infrastructure.config.settings import get_settings


def setup_logging(log_name: str = "app", filename_prefix: str = "app") -> logging.Logger:
    settings = get_settings()
    settings.logs_path.mkdir(parents=True, exist_ok=True)

    log_file = Path(settings.logs_path) / f"{filename_prefix}_{datetime.now().strftime('%Y%m%d')}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    has_managed_stream = any(getattr(h, "_scraper_stream_handler", False) for h in logger.handlers)
    if not has_managed_stream:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler._scraper_stream_handler = True  # type: ignore[attr-defined]
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    has_managed_file = any(getattr(h, "_scraper_file_handler", False) for h in logger.handlers)
    if not has_managed_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler._scraper_file_handler = True  # type: ignore[attr-defined]
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_with_context(logger: logging.Logger, level: int, message: str, **context: str) -> None:
    context_text = " ".join(f"{key}={value}" for key, value in context.items() if value is not None)
    if context_text:
        logger.log(level, f"{message} | {context_text}")
    else:
        logger.log(level, message)
