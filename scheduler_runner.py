"""
Scheduler Runner - Executa scraper em intervalos regulares
Mantém o programa rodando continuamente (SEM DEPENDÊNCIAS EXTERNAS)
"""

import asyncio
import time
import logging
import sys
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper_ml_afiliado import ScraperMLAfiliado

class ScraperScheduler:
    def __init__(self, intervalo_minutos=30, max_produtos=50):
        self.intervalo_minutos = intervalo_minutos
        self.max_produtos = max_produtos
        self.rodando = False
        self.proximo_run = None
        self.setup_logging()
        
    def setup_logging(self):
        """Configura logging para o scheduler"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)

    async def executar_scraping(self):
        """Executa uma sessão de scraping"""
        try:
            self.logger.info(f"🚀 Iniciando scraping agendado - {self.max_produtos} produtos")
            
            async with ScraperMLAfiliado(
                headless=True,  # Execução em background
                max_produtos=self.max_produtos,
                usar_cache=True
            ) as scraper:
                
                # Verifica se precisa fazer login
                if not await scraper.verificar_login():
                    self.logger.warning("⚠️ Login necessário - scraping cancelado")
                    return
                
                # Executa scraping
                produtos = await scraper.scrape_ofertas()
                
                # Salva resultados
                if produtos:
                    arquivo = await scraper.salvar_resultados(produtos)
                    
                    sucesso = sum(1 for p in produtos if p["status"] == "sucesso")
                    total = len(produtos)
                    
                    self.logger.info(f"✅ Scraping concluído: {sucesso}/{total} produtos com link")
                    self.logger.info(f"💾 Resultados salvos: {arquivo}")
                    
                    # Estatísticas do cache
                    if scraper.usar_cache:
                        stats = scraper.estatisticas_cache()
                        self.logger.info(f"📊 Cache total: {stats['total_produtos']} produtos")
                else:
                    self.logger.info("🎯 Nenhum produto novo encontrado")
                    
        except Exception as e:
            self.logger.error(f"❌ Erro no scraping agendado: {e}")
            import traceback
            self.logger.error(f"📋 Stack trace: {traceback.format_exc()}")

    def job_wrapper(self):
        """Wrapper para executar job assíncrono"""
        try:
            asyncio.run(self.executar_scraping())
        except Exception as e:
            self.logger.error(f"❌ Erro crítico no scheduler: {e}")

    def calcular_proximo_run(self):
        """Calcula horário da próxima execução"""
        self.proximo_run = datetime.now() + timedelta(minutes=self.intervalo_minutos)
        return self.proximo_run

    def iniciar_scheduler(self):
        """Inicia o scheduler contínuo"""
        self.logger.info("="*60)
        self.logger.info("🕐 SCHEDULER SCRAPER ML - egnOfertas")
        self.logger.info("="*60)
        self.logger.info(f"⏰ Intervalo: {self.intervalo_minutos} minutos")
        self.logger.info(f"📦 Max produtos: {self.max_produtos}")
        
        self.rodando = True
        
        # Execução inicial
        self.logger.info("🔄 Executando primeira sessão...")
        self.job_wrapper()
        
        # Calcula próxima execução
        self.calcular_proximo_run()
        self.logger.info(f"🚀 Próxima execução: {self.proximo_run.strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Loop principal
        try:
            while self.rodando:
                agora = datetime.now()
                
                # Verifica se é hora de executar
                if agora >= self.proximo_run:
                    self.logger.info(f"⏰ Hora de executar - {agora.strftime('%H:%M:%S')}")
                    self.job_wrapper()
                    
                    # Calcula próxima execução
                    self.calcular_proximo_run()
                    self.logger.info(f"🚀 Próxima execução: {self.proximo_run.strftime('%d/%m/%Y %H:%M:%S')}")
                
                # Aguarda 1 minuto antes de verificar novamente
                time.sleep(60)
                
                # Log de status a cada hora
                if agora.minute == 0:
                    tempo_restante = self.proximo_run - agora
                    minutos_restantes = int(tempo_restante.total_seconds() / 60)
                    self.logger.info(f"💓 Scheduler ativo - {minutos_restantes} min para próxima execução")
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 Scheduler interrompido pelo usuário")
            self.rodando = False
        except Exception as e:
            self.logger.error(f"❌ Erro crítico no scheduler: {e}")
            self.rodando = False

    def parar_scheduler(self):
        """Para o scheduler"""
        self.rodando = False
        self.logger.info("🛑 Parando scheduler...")

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scheduler para Scraper ML')
    parser.add_argument('--intervalo', type=int, default=30, 
                       help='Intervalo em minutos (padrão: 30)')
    parser.add_argument('--produtos', type=int, default=50,
                       help='Número máximo de produtos (padrão: 50)')
    parser.add_argument('--agora', action='store_true',
                       help='Executa uma vez agora e sai')
    
    args = parser.parse_args()
    
    scheduler = ScraperScheduler(
        intervalo_minutos=args.intervalo,
        max_produtos=args.produtos
    )
    
    if args.agora:
        # Execução única
        scheduler.logger.info("🔄 Execução única solicitada")
        scheduler.job_wrapper()
    else:
        # Scheduler contínuo
        scheduler.iniciar_scheduler()

if __name__ == "__main__":
    main()