from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScrapeResultDTO:
    scraper_type: str
    total_coletados: int = 0
    novos: int = 0
    existentes: int = 0
    erros: int = 0
    itens: list[dict[str, Any]] = field(default_factory=list)
    detalhes_erros: list[str] = field(default_factory=list)

    @property
    def total_processados(self) -> int:
        return self.novos + self.existentes + self.erros
