from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScrapeRequestDTO:
    scraper_type: str
    max_items: int = 30
    headless: bool = True
    url: Optional[str] = None
