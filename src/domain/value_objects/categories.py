from __future__ import annotations

import re
import unicodedata
from typing import Iterable


# Categorias top-level divulgadas nas docs da API de categorias do Mercado Livre (site MLB).
MERCADO_LIVRE_TOP_CATEGORIES_BR = [
    "Acessorios para Veiculos",
    "Agro",
    "Alimentos e Bebidas",
    "Animais",
    "Antiguidades e Colecoes",
    "Arte, Papelaria e Armarinho",
    "Bebes",
    "Beleza e Cuidado Pessoal",
    "Brinquedos e Hobbies",
    "Calcados, Roupas e Bolsas",
    "Cameras e Acessorios",
    "Carros, Motos e Outros",
]

# Presets amigaveis para selecao rapida na GUI.
GUI_CATEGORY_PRESETS = [
    "Todas",
    "Eletronicos",
    "Vestuario",
    "Casa e Decoracao",
    "Esportes e Fitness",
]


def gui_category_options() -> list[str]:
    options = []
    for value in GUI_CATEGORY_PRESETS + MERCADO_LIVRE_TOP_CATEGORIES_BR:
        if value not in options:
            options.append(value)
    return options


def normalize_category_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = " ".join(normalized.split())
    return normalized


_CATEGORY_ALIASES = {
    "eletronicos": "eletronicos",
    "vestuario": "calcados roupas e bolsas",
    "casa e decoracao": "casa moveis e decoracao",
    "esportes e fitness": "esportes e fitness",
}


def _split_category_values(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,\n;]+", value) if part.strip()]


def _normalize_single_category_filter(value: str | None) -> str | None:
    normalized = normalize_category_text(value)
    if not normalized or normalized in {"todas", "todos", "all", "sem filtro"}:
        return None
    return _CATEGORY_ALIASES.get(normalized, normalized)


def resolve_category_filters(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = _split_category_values(value)
    else:
        raw_values = []
        for item in value:
            raw_values.extend(_split_category_values(str(item)))

    resolved: list[str] = []
    for item in raw_values:
        normalized = _normalize_single_category_filter(item)
        if normalized and normalized not in resolved:
            resolved.append(normalized)
    return resolved


def resolve_category_filter(value: str | None) -> str | None:
    resolved = resolve_category_filters(value)
    if not resolved:
        return None
    return resolved[0]


def category_matches(category_filter: str | Iterable[str] | None, product_category: str | None) -> bool:
    resolved_filters = resolve_category_filters(category_filter)
    if not resolved_filters:
        return True
    product_normalized = normalize_category_text(product_category)
    if not product_normalized:
        return False
    return any(resolved_filter in product_normalized for resolved_filter in resolved_filters)
