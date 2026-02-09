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

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def log_with_context(logger: logging.Logger, level: int, message: str, **context: str) -> None:
    context_text = " ".join(f"{key}={value}" for key, value in context.items() if value is not None)
    if context_text:
        logger.log(level, f"{message} | {context_text}")
    else:
        logger.log(level, message)
