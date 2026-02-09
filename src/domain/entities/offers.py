from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from src.domain.value_objects.dedupe import build_offer_dedupe_key, extract_mlb_id, normalize_url


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


@dataclass
class OfferEntity:
    url_original: str
    nome: Optional[str] = None
    mlb_id: Optional[str] = None
    product_id: Optional[str] = None
    url_curta: Optional[str] = None
    url_afiliado: Optional[str] = None
    foto_url: Optional[str] = None
    preco_atual: Optional[Decimal] = None
    preco_original: Optional[Decimal] = None
    desconto: Optional[int] = None
    status: str = "ativo"
    chave_dedupe: str = field(default="")
    tempo_para_acabar: Optional[str] = None

    @classmethod
    def from_raw(cls, payload: dict[str, Any], include_tempo: bool = False) -> "OfferEntity":
        normalized_url = normalize_url(payload.get("url_original", ""))
        mlb_id = payload.get("mlb_id") or extract_mlb_id(normalized_url)
        product_id = (payload.get("product_id") or "").strip() or None
        nome = (payload.get("nome") or "").strip() or None
        url_curta = (payload.get("url_curta") or "").strip() or None
        url_afiliado = (payload.get("url_afiliado") or "").strip() or None
        foto_url = (payload.get("foto_url") or "").strip() or None
        status = (payload.get("status") or "ativo").strip() or "ativo"
        tempo = (payload.get("tempo_para_acabar") or "").strip() or None if include_tempo else None

        entity = cls(
            mlb_id=mlb_id,
            url_original=normalized_url,
            url_curta=url_curta,
            url_afiliado=url_afiliado,
            product_id=product_id,
            nome=nome,
            foto_url=foto_url,
            preco_atual=_to_decimal(payload.get("preco_atual")),
            preco_original=_to_decimal(payload.get("preco_original")),
            desconto=_to_int(payload.get("desconto")),
            status=status,
            tempo_para_acabar=tempo,
        )
        entity.chave_dedupe = build_offer_dedupe_key(entity.mlb_id, entity.product_id, entity.url_original)
        return entity

    def minimal_required(self) -> bool:
        return bool(self.url_original and self.chave_dedupe)
