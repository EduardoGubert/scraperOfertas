from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


def _normalize_decimal_token(token: str) -> str | None:
    raw = token.strip()
    if not raw:
        return None

    sign = "-" if raw.startswith("-") else ""
    core = raw[1:] if sign else raw
    core = re.sub(r"[^0-9,.]", "", core)
    if not core or not re.search(r"\d", core):
        return None

    has_comma = "," in core
    has_dot = "." in core

    if has_comma and has_dot:
        decimal_sep = "," if core.rfind(",") > core.rfind(".") else "."
        thousand_sep = "." if decimal_sep == "," else ","
        integer_part, decimal_part = core.rsplit(decimal_sep, 1)
        integer_digits = integer_part.replace(thousand_sep, "").replace(decimal_sep, "")
        decimal_digits = decimal_part.replace(thousand_sep, "").replace(decimal_sep, "")
        if not integer_digits and not decimal_digits:
            return None
        return f"{sign}{integer_digits}.{decimal_digits}" if decimal_digits else f"{sign}{integer_digits}"

    if has_comma or has_dot:
        sep = "," if has_comma else "."
        integer_part, decimal_part = core.rsplit(sep, 1)
        fractional_len = len(decimal_part)
        if fractional_len == 3:
            normalized = core.replace(sep, "")
            return f"{sign}{normalized}" if normalized else None

        integer_digits = integer_part.replace(sep, "")
        decimal_digits = decimal_part.replace(sep, "")
        if not integer_digits and not decimal_digits:
            return None
        return f"{sign}{integer_digits}.{decimal_digits}" if decimal_digits else f"{sign}{integer_digits}"

    return f"{sign}{core}"


def parse_decimal_from_text(text: str | None) -> Decimal | None:
    if not text:
        return None

    match = re.search(r"-?\d[\d.,]*", text)
    if not match:
        return None

    normalized = _normalize_decimal_token(match.group(0))
    if not normalized:
        return None

    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError, ArithmeticError):
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
