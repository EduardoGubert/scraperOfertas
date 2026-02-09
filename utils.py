"""Utilitarios de compatibilidade para normalizacao e deduplicacao."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.domain.entities.offers import OfferEntity
from src.domain.value_objects.dedupe import build_offer_dedupe_key, extract_mlb_id, normalize_url


def normalizar_url(url: str) -> str:
    return normalize_url(url)


def extrair_mlb_id(url: str) -> Optional[str]:
    return extract_mlb_id(url)


def gerar_chave_dedupe(produto: Dict) -> str:
    return build_offer_dedupe_key(
        mlb_id=produto.get("mlb_id"),
        product_id=produto.get("product_id"),
        url_original=produto.get("url_original", ""),
    )


def normalizar_dados_produto(produto_raw: Dict) -> Dict[str, Any]:
    entity = OfferEntity.from_raw(produto_raw)
    return {
        "mlb_id": entity.mlb_id,
        "url_original": entity.url_original,
        "url_curta": entity.url_curta,
        "url_afiliado": entity.url_afiliado,
        "product_id": entity.product_id,
        "nome": entity.nome,
        "foto_url": entity.foto_url,
        "preco_atual": entity.preco_atual,
        "preco_original": entity.preco_original,
        "desconto": entity.desconto,
        "status": entity.status,
        "chave_dedupe": entity.chave_dedupe,
    }


def validar_produto(produto: Dict) -> tuple[bool, str]:
    if not produto.get("url_original"):
        return False, "URL original e obrigatoria"
    if not produto.get("chave_dedupe"):
        return False, "Chave de deduplicacao nao foi gerada"
    return True, "Produto valido"
