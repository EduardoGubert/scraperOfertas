from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from src.domain.value_objects.dedupe import build_coupon_dedupe_key, normalize_url


def _decimal_or_none(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _int_or_none(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


@dataclass
class CouponEntity:
    nome: Optional[str]
    desconto_texto: Optional[str]
    desconto_percentual: Optional[int]
    desconto_valor: Optional[Decimal]
    limite_condicoes: Optional[str]
    imagem_url: Optional[str]
    url_origem: Optional[str]
    raw_payload: dict[str, Any]
    status: str = "ativo"
    chave_dedupe: str = field(default="")

    @classmethod
    def from_raw(cls, payload: dict[str, Any], source_url: str) -> "CouponEntity":
        nome = (payload.get("nome") or "").strip() or None
        desconto_texto = (payload.get("desconto_texto") or "").strip() or None
        limite = (payload.get("limite_condicoes") or "").strip() or None
        imagem_url = (payload.get("imagem_url") or "").strip() or None
        url_origem = (payload.get("url_origem") or source_url or "").strip() or None

        entity = cls(
            nome=nome,
            desconto_texto=desconto_texto,
            desconto_percentual=_int_or_none(payload.get("desconto_percentual")),
            desconto_valor=_decimal_or_none(payload.get("desconto_valor")),
            limite_condicoes=limite,
            imagem_url=imagem_url,
            url_origem=normalize_url(url_origem) if url_origem else None,
            raw_payload=payload,
            status=(payload.get("status") or "ativo").strip() or "ativo",
        )
        entity.chave_dedupe = build_coupon_dedupe_key(entity.url_origem, entity.nome, entity.desconto_texto)
        return entity

    def minimal_required(self) -> bool:
        return bool(self.chave_dedupe and self.url_origem)
