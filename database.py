"""Camada de compatibilidade para acesso ao banco.
Mantem assinatura aproximada do DatabaseManager legado.
"""

from __future__ import annotations

from typing import Any, Optional

from src.domain.entities.offers import OfferEntity
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.postgres import PostgresConnection
from src.infrastructure.persistence.repositories import PostgresOfferRepository


class DatabaseManager:
    def __init__(self):
        self.settings = get_settings()
        self.connection = PostgresConnection(self.settings)
        self.offer_repo = PostgresOfferRepository(self.connection)

    async def connect(self):
        await self.connection.connect()

    async def close(self):
        await self.connection.close()

    async def ensure_schema(self):
        # Schema agora e gerenciado via Alembic.
        return

    async def produto_existe(self, chave_dedupe: str, produto: dict) -> bool:
        return await self.offer_repo.exists_offer("ml_ofertas", chave_dedupe, produto.get("mlb_id"))

    async def salvar_produto(self, produto: dict) -> Optional[int]:
        offer = OfferEntity.from_raw(produto)
        product_id, _ = await self.offer_repo.upsert_offer("ml_ofertas", offer, include_tempo=False)
        return product_id

    async def get_stats(self) -> dict[str, int]:
        return await self.offer_repo.get_table_stats("ml_ofertas")
