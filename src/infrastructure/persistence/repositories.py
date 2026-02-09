from __future__ import annotations

import json
from typing import Any

from src.domain.entities.coupons import CouponEntity
from src.domain.entities.offers import OfferEntity
from src.domain.interfaces.repositories import ICouponRepository, IOfferRepository
from src.domain.value_objects.timezone import now_sao_paulo
from src.infrastructure.persistence.postgres import PostgresConnection


class PostgresOfferRepository(IOfferRepository):
    def __init__(self, connection: PostgresConnection):
        self.connection = connection

    async def exists_offer(self, table: str, chave_dedupe: str, mlb_id: str | None) -> bool:
        pool = self.connection.require_pool()
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                f"SELECT 1 FROM {table} WHERE chave_dedupe = $1 LIMIT 1",  # nosec B608
                chave_dedupe,
            )
            if exists:
                return True

            if mlb_id:
                exists = await conn.fetchval(
                    f"SELECT 1 FROM {table} WHERE mlb_id = $1 LIMIT 1",  # nosec B608
                    mlb_id,
                )
                return bool(exists)
            return False

    async def upsert_offer(self, table: str, offer: OfferEntity, include_tempo: bool = False) -> tuple[int, bool]:
        pool = self.connection.require_pool()
        # Compatibilidade com bases legadas que ainda usam TIMESTAMP sem timezone.
        current_time = now_sao_paulo().replace(tzinfo=None)

        if include_tempo:
            insert_sql = f"""
            INSERT INTO {table} (
                mlb_id, chave_dedupe, url_original, url_curta, url_afiliado, product_id,
                nome, foto_url, preco_atual, preco_original, desconto, status,
                tempo_para_acabar, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11, $12,
                $13, $14, $14
            )
            ON CONFLICT (chave_dedupe)
            DO UPDATE SET
                mlb_id = EXCLUDED.mlb_id,
                url_original = EXCLUDED.url_original,
                url_curta = EXCLUDED.url_curta,
                url_afiliado = EXCLUDED.url_afiliado,
                product_id = EXCLUDED.product_id,
                nome = EXCLUDED.nome,
                foto_url = EXCLUDED.foto_url,
                preco_atual = EXCLUDED.preco_atual,
                preco_original = EXCLUDED.preco_original,
                desconto = EXCLUDED.desconto,
                status = EXCLUDED.status,
                tempo_para_acabar = EXCLUDED.tempo_para_acabar,
                updated_at = EXCLUDED.updated_at
            RETURNING id, (xmax = 0) AS inserted;
            """
            params: tuple[Any, ...] = (
                offer.mlb_id,
                offer.chave_dedupe,
                offer.url_original,
                offer.url_curta,
                offer.url_afiliado,
                offer.product_id,
                offer.nome,
                offer.foto_url,
                offer.preco_atual,
                offer.preco_original,
                offer.desconto,
                offer.status,
                offer.tempo_para_acabar,
                current_time,
            )
        else:
            insert_sql = f"""
            INSERT INTO {table} (
                mlb_id, chave_dedupe, url_original, url_curta, url_afiliado, product_id,
                nome, foto_url, preco_atual, preco_original, desconto, status,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11, $12,
                $13, $13
            )
            ON CONFLICT (chave_dedupe)
            DO UPDATE SET
                mlb_id = EXCLUDED.mlb_id,
                url_original = EXCLUDED.url_original,
                url_curta = EXCLUDED.url_curta,
                url_afiliado = EXCLUDED.url_afiliado,
                product_id = EXCLUDED.product_id,
                nome = EXCLUDED.nome,
                foto_url = EXCLUDED.foto_url,
                preco_atual = EXCLUDED.preco_atual,
                preco_original = EXCLUDED.preco_original,
                desconto = EXCLUDED.desconto,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            RETURNING id, (xmax = 0) AS inserted;
            """
            params = (
                offer.mlb_id,
                offer.chave_dedupe,
                offer.url_original,
                offer.url_curta,
                offer.url_afiliado,
                offer.product_id,
                offer.nome,
                offer.foto_url,
                offer.preco_atual,
                offer.preco_original,
                offer.desconto,
                offer.status,
                current_time,
            )

        async with pool.acquire() as conn:
            row = await conn.fetchrow(insert_sql, *params)
            if not row:
                raise RuntimeError("Falha ao persistir oferta")
            return int(row["id"]), bool(row["inserted"])

    async def get_table_stats(self, table: str) -> dict[str, int]:
        pool = self.connection.require_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")  # nosec B608
            com_link = await conn.fetchval(
                f"SELECT COUNT(*) FROM {table} WHERE url_curta IS NOT NULL"  # nosec B608
            )
            return {
                "total": int(total or 0),
                "com_link": int(com_link or 0),
                "sem_link": int((total or 0) - (com_link or 0)),
            }


class PostgresCouponRepository(ICouponRepository):
    def __init__(self, connection: PostgresConnection):
        self.connection = connection

    async def exists_coupon(self, chave_dedupe: str) -> bool:
        pool = self.connection.require_pool()
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM ml_cupons WHERE chave_dedupe = $1 LIMIT 1",
                chave_dedupe,
            )
            return bool(exists)

    async def upsert_coupon(self, coupon: CouponEntity) -> tuple[int, bool]:
        pool = self.connection.require_pool()
        # Compatibilidade com bases legadas que ainda usam TIMESTAMP sem timezone.
        current_time = now_sao_paulo().replace(tzinfo=None)

        insert_sql = """
        INSERT INTO ml_cupons (
            nome, desconto_texto, desconto_percentual, desconto_valor,
            limite_condicoes, imagem_url, url_origem, status, chave_dedupe,
            raw_payload, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4,
            $5, $6, $7, $8, $9,
            $10, $11, $11
        )
        ON CONFLICT (chave_dedupe)
        DO UPDATE SET
            nome = EXCLUDED.nome,
            desconto_texto = EXCLUDED.desconto_texto,
            desconto_percentual = EXCLUDED.desconto_percentual,
            desconto_valor = EXCLUDED.desconto_valor,
            limite_condicoes = EXCLUDED.limite_condicoes,
            imagem_url = EXCLUDED.imagem_url,
            url_origem = EXCLUDED.url_origem,
            status = EXCLUDED.status,
            raw_payload = EXCLUDED.raw_payload,
            updated_at = EXCLUDED.updated_at
        RETURNING id, (xmax = 0) AS inserted;
        """

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                insert_sql,
                coupon.nome,
                coupon.desconto_texto,
                coupon.desconto_percentual,
                coupon.desconto_valor,
                coupon.limite_condicoes,
                coupon.imagem_url,
                coupon.url_origem,
                coupon.status,
                coupon.chave_dedupe,
                json.dumps(coupon.raw_payload, ensure_ascii=False),
                current_time,
            )
            if not row:
                raise RuntimeError("Falha ao persistir cupom")
            return int(row["id"]), bool(row["inserted"])

    async def get_table_stats(self) -> dict[str, int]:
        pool = self.connection.require_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM ml_cupons")
            return {"total": int(total or 0)}
