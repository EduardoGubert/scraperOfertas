from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if normalized.endswith("/") and parsed.path and parsed.path != "/":
        normalized = normalized[:-1]
    return normalized.lower()


def extract_mlb_id(value: str) -> Optional[str]:
    if not value:
        return None
    patterns = [
        r"MLB[-]?(\d{8,12})",
        r"/p/MLB(\d{8,12})",
        r"mlb[-]?(\d{8,12})",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return f"MLB{match.group(1)}"
    return None


def short_hash(value: str, length: int = 16) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()[:length]


def build_offer_dedupe_key(mlb_id: Optional[str], product_id: Optional[str], url_original: str) -> str:
    if mlb_id:
        return f"mlb:{mlb_id}"
    if product_id:
        return f"pid:{product_id}"
    normalized = normalize_url(url_original)
    if normalized:
        return f"url:{short_hash(normalized)}"
    return f"fb:{short_hash('offer-fallback')}"


def build_coupon_dedupe_key(url_origem: Optional[str], nome: Optional[str], desconto_texto: Optional[str]) -> str:
    parts = [
        normalize_url(url_origem or ""),
        (nome or "").strip().lower(),
        (desconto_texto or "").strip().lower(),
    ]
    joined = "|".join(parts)
    return f"coupon:{short_hash(joined)}"


@dataclass(frozen=True)
class CacheKey:
    scraper_type: str
    dedupe_key: str

    def value(self) -> str:
        return f"{self.scraper_type}:{self.dedupe_key}"
