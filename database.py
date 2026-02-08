"""
Módulo de Banco de Dados para Pipeline ML
Gerencia conexão, schema e operações CRUD com PostgreSQL
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import asyncpg
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gerenciador de banco de dados PostgreSQL"""
    
    def __init__(self):
        self.pool = None
        self.demo_mode = False  # Modo de demonstração
        self.demo_data = []     # Dados simulados em memória
        
        # Configuração via ambiente
        self.connection_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASS'),
        }
        
        # Validação
        if not all([self.connection_config['database'], 
                   self.connection_config['user'], 
                   self.connection_config['password']]):
            raise ValueError("Configuração de banco incompleta no .env")
    
    async def connect(self):
        """Inicializa pool de conexões"""
        try:
            self.pool = await asyncpg.create_pool(
                **self.connection_config,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            logger.info(f"✅ Conexão com banco estabelecida: {self.connection_config['host']}")
            
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível conectar ao banco: {e}")
            logger.info("🔄 Ativando modo de DEMONSTRAÇÃO (dados em memória)")
            self.demo_mode = True
            self.pool = None
    
    async def close(self):
        """Fecha pool de conexões"""
        if self.pool:
            await self.pool.close()
            logger.info("🔄 Conexões de banco fechadas")
    
    async def ensure_schema(self):
        """Cria tabela ml_ofertas se não existir"""
        if self.demo_mode:
            logger.info("✅ Schema simulado criado (modo demonstração)")
            return
            
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS ml_ofertas (
            id SERIAL PRIMARY KEY,
            mlb_id VARCHAR(50) UNIQUE,
            url_original TEXT NOT NULL,
            url_curta TEXT,
            url_afiliado TEXT,
            product_id VARCHAR(100),
            nome TEXT,
            foto_url TEXT,
            preco_atual DECIMAL(10,2),
            preco_original DECIMAL(10,2),
            desconto INTEGER,
            status VARCHAR(20) DEFAULT 'ativo',
            chave_dedupe VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Índices para performance
        CREATE INDEX IF NOT EXISTS idx_ml_ofertas_mlb_id ON ml_ofertas(mlb_id);
        CREATE INDEX IF NOT EXISTS idx_ml_ofertas_chave_dedupe ON ml_ofertas(chave_dedupe);
        CREATE INDEX IF NOT EXISTS idx_ml_ofertas_created_at ON ml_ofertas(created_at);
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(create_table_sql)
                logger.info("✅ Schema de banco verificado/criado")
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar schema: {e}")
            raise
    
    async def produto_existe(self, chave_dedupe: str, produto: Dict) -> bool:
        """
        Verifica se produto já existe no banco
        
        Args:
            chave_dedupe: Chave única de deduplicação
            produto: Dados do produto (para fallback)
            
        Returns:
            True se produto já existe
        """
        if self.demo_mode:
            # Simula verificação em dados de memória
            for item in self.demo_data:
                if item.get('chave_dedupe') == chave_dedupe:
                    return True
                if produto.get('mlb_id') and item.get('mlb_id') == produto.get('mlb_id'):
                    return True
            return False
            
        try:
            async with self.pool.acquire() as conn:
                # Busca por chave de deduplicação (método primário)
                result = await conn.fetchval(
                    "SELECT id FROM ml_ofertas WHERE chave_dedupe = $1 LIMIT 1",
                    chave_dedupe
                )
                
                if result:
                    return True
                
                # Fallback: busca por MLB ID se existir
                if produto.get('mlb_id'):
                    result = await conn.fetchval(
                        "SELECT id FROM ml_ofertas WHERE mlb_id = $1 LIMIT 1",
                        produto['mlb_id']
                    )
                    return bool(result)
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar existência: {e}")
            return False  # Em caso de erro, assume que não existe (será tentativa de insert)
    
    async def salvar_produto(self, produto: Dict) -> Optional[int]:
        """
        Salva novo produto no banco (UPSERT)
        
        Args:
            produto: Dados normalizados do produto
            
        Returns:
            ID do produto inserido/atualizado
        """
        if self.demo_mode:
            # Simula inserção em dados de memória
            produto_id = len(self.demo_data) + 1
            produto_simulated = produto.copy()
            produto_simulated['id'] = produto_id
            self.demo_data.append(produto_simulated)
            return produto_id
            
        insert_sql = """
        INSERT INTO ml_ofertas (
            mlb_id, url_original, url_curta, url_afiliado, product_id,
            nome, foto_url, preco_atual, preco_original, desconto,
            status, chave_dedupe, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW()
        )
        ON CONFLICT (chave_dedupe) 
        DO UPDATE SET
            url_curta = EXCLUDED.url_curta,
            url_afiliado = EXCLUDED.url_afiliado,
            preco_atual = EXCLUDED.preco_atual,
            preco_original = EXCLUDED.preco_original,
            desconto = EXCLUDED.desconto,
            updated_at = NOW()
        RETURNING id;
        """
        
        try:
            async with self.pool.acquire() as conn:
                produto_id = await conn.fetchval(
                    insert_sql,
                    produto.get('mlb_id'),
                    produto['url_original'], 
                    produto.get('url_curta'),
                    produto.get('url_afiliado'),
                    produto.get('product_id'),
                    produto.get('nome'),
                    produto.get('foto_url'),
                    produto.get('preco_atual'),
                    produto.get('preco_original'), 
                    produto.get('desconto'),
                    produto.get('status', 'ativo'),
                    produto['chave_dedupe']
                )
                
                return produto_id
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar produto: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas da tabela"""
        try:
            async with self.pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM ml_ofertas")
                com_link = await conn.fetchval("SELECT COUNT(*) FROM ml_ofertas WHERE url_curta IS NOT NULL")
                hoje = await conn.fetchval("SELECT COUNT(*) FROM ml_ofertas WHERE created_at::date = CURRENT_DATE")
                
                return {
                    'total': total,
                    'com_link': com_link, 
                    'sem_link': total - com_link,
                    'hoje': hoje
                }
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {}