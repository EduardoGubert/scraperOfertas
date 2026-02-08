#!/usr/bin/env python3
"""
Pipeline de Scraping ML com Banco de Dados
Entrypoint principal que orquestra: scraping → deduplicação → persistência

Uso:
    python pipeline.py --max-produtos 50
    python pipeline.py  # Input interativo
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import List, Dict, Optional

from scraper_ml_afiliado import ScraperMLAfiliado
from database import DatabaseManager
from utils import normalizar_dados_produto, gerar_chave_dedupe
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'pipeline_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ScrapingPipeline:
    """Pipeline principal de scraping com persistência em banco"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.scraper = None
        
        # Configurações via ambiente
        self.headless = os.getenv('SCRAPER_HEADLESS', 'false').lower() == 'true'
        self.wait_ms = int(os.getenv('SCRAPER_WAIT_MS', '1500'))
        
    async def __aenter__(self):
        """Context manager - inicialização"""
        await self.db_manager.connect()
        await self.db_manager.ensure_schema()
        
        self.scraper = ScraperMLAfiliado(
            headless=self.headless,
            wait_ms=self.wait_ms,
            max_produtos=1000  # Será limitado pelo parâmetro do usuário
        )
        await self.scraper._init_browser()
        
        logger.info("✅ Pipeline inicializado: banco + scraper prontos")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager - cleanup"""
        if self.scraper:
            await self.scraper._close_browser()
        await self.db_manager.close()
        logger.info("🔄 Pipeline finalizado: recursos liberados")

    async def processar_produtos(self, max_produtos: int) -> Dict[str, int]:
        """
        Executa o pipeline completo: scraping → deduplicação → persistência
        
        Args:
            max_produtos: Limite de produtos a processar
            
        Returns:
            Dict com contadores: novos, existentes, erros
        """
        logger.info(f"🚀 Iniciando pipeline: {max_produtos} produtos máximo")
        
        # Contadores para relatório final
        stats = {"novos": 0, "existentes": 0, "erros": 0}
        
        try:
            # 1. Executa scraping (usando classe existente)
            logger.info("📡 Iniciando scraping com Playwright...")
            produtos_raw = await self.scraper.scrape_ofertas(max_produtos=max_produtos)
            logger.info(f"✅ Scraping concluído: {len(produtos_raw)} produtos coletados")
            
            # 2. Processa cada produto individualmente
            for i, produto_raw in enumerate(produtos_raw, 1):
                logger.info(f"[{i}/{len(produtos_raw)}] Processando: {produto_raw.get('nome', 'N/A')[:50]}...")
                
                try:
                    # Normaliza dados
                    produto = normalizar_dados_produto(produto_raw)
                    chave_dedupe = gerar_chave_dedupe(produto)
                    
                    # Verifica se já existe (por chave de deduplicação)
                    existe = await self.db_manager.produto_existe(chave_dedupe, produto)
                    
                    if existe:
                        logger.info(f"    ⏭️ Produto já cadastrado, pulando...")
                        stats["existentes"] += 1
                    else:
                        # Salva novo produto
                        produto_id = await self.db_manager.salvar_produto(produto)
                        logger.info(f"    ✅ Novo produto salvo (ID: {produto_id})")
                        stats["novos"] += 1
                        
                except Exception as e:
                    logger.error(f"    ❌ Erro ao processar produto: {e}")
                    stats["erros"] += 1
                    
        except Exception as e:
            logger.error(f"❌ Erro crítico no pipeline: {e}")
            raise
            
        # Relatório final
        total = stats["novos"] + stats["existentes"] + stats["erros"]
        logger.info(f"""
        === RELATÓRIO FINAL ===
        ✅ Novos produtos: {stats['novos']}
        ⏭️ Já existentes: {stats['existentes']}  
        ❌ Erros: {stats['erros']}
        📊 Total processado: {total}
        ========================
        """)
        
        return stats


def obter_max_produtos() -> int:
    """Obtém número de produtos via CLI ou input interativo"""
    parser = argparse.ArgumentParser(description='Pipeline de Scraping ML com Banco')
    parser.add_argument(
        '--max-produtos', 
        type=int, 
        help='Número máximo de produtos a processar'
    )
    
    args = parser.parse_args()
    
    if args.max_produtos:
        return args.max_produtos
    
    # Input interativo como fallback
    while True:
        try:
            resposta = input("\nQuantos produtos deseja processar? [padrão: 20]: ").strip()
            return int(resposta) if resposta else 20
        except ValueError:
            print("Por favor, digite um número válido.")


async def main():
    """Função principal"""
    print("\n" + "="*60)
    print("PIPELINE SCRAPING ML -> BANCO DE DADOS")
    print("="*60)
    
    # Validação de ambiente
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Variáveis de ambiente faltando: {missing_vars}")
        logger.error("Configure o arquivo .env baseado no .env.example")
        return
    
    # Obter parâmetros
    max_produtos = obter_max_produtos()
    logger.info(f"Configuração: {max_produtos} produtos, headless={os.getenv('SCRAPER_HEADLESS', 'false')}")
    
    # Executar pipeline
    try:
        async with ScrapingPipeline() as pipeline:
            stats = await pipeline.processar_produtos(max_produtos)
            
        print(f"\nPipeline concluído com sucesso!")
        print(f"Novos: {stats['novos']} | Existentes: {stats['existentes']} | Erros: {stats['erros']}")
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())