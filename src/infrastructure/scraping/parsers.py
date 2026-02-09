from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


def parse_decimal_from_text(text: str | None) -> Decimal | None:
    if not text:
        return None
    cleaned = text.replace("R$", "").replace(".", "").replace(",", ".")
    match = re.search(r"(-?\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except (InvalidOperation, ValueError):
        return None


def parse_percent_from_text(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d{1,3})\s*%", text)
    if not match:
        return None
    return int(match.group(1))


def parse_tempo_para_acabar(raw_text: str | None) -> str | None:
    if not raw_text:
        return None
    normalized = " ".join(raw_text.split())
    return normalized or None


def parse_coupon_card(raw: dict[str, Any]) -> dict[str, Any]:
    nome = (raw.get("nome") or "").strip() or None
    desconto_texto = (raw.get("desconto_texto") or "").strip() or None
    limite_condicoes = (raw.get("limite_condicoes") or "").strip() or None
    imagem_url = (raw.get("imagem_url") or "").strip() or None
    url_origem = (raw.get("url_origem") or "").strip() or None

    desconto_percentual = parse_percent_from_text(desconto_texto)
    desconto_valor = parse_decimal_from_text(desconto_texto) if not desconto_percentual else None

    return {
        "nome": nome,
        "desconto_texto": desconto_texto,
        "desconto_percentual": desconto_percentual,
        "desconto_valor": desconto_valor,
        "limite_condicoes": limite_condicoes,
        "imagem_url": imagem_url,
        "url_origem": url_origem,
        "status": (raw.get("status") or "ativo").strip() or "ativo",
        "raw_payload": raw,
    }
