#!/usr/bin/env python3
"""
==============================================
FLUXO DE LOGIN PARA VPS
==============================================

PROBLEMA:
- VPS não tem tela
- Não consegue fazer login manual
- CAPTCHA não carrega em headless

SOLUÇÃO:
1. Roda este script NA SUA MÁQUINA (com tela)
2. Faz login normalmente
3. Copia a pasta ml_browser_data/ para a VPS
4. VPS usa os cookies salvos

==============================================
"""

import asyncio
import shutil
import os
from pathlib import Path
from scraper_ml_afiliado import ScraperMLAfiliado


# Configurações
BROWSER_DATA_DIR = "./ml_browser_data"
EXPORT_ZIP = "ml_cookies_export.tar.gz"


async def fazer_login_e_exportar():
    """
    Faz login manual e prepara para exportar para VPS
    """
    print("\n" + "="*60)
    print("🔐 LOGIN PARA VPS - MERCADO LIVRE AFILIADO")
    print("="*60)
    print("""
    
    Este script deve ser executado NA SUA MÁQUINA LOCAL
    (não na VPS!)
    
    O que vai acontecer:
    1. Navegador abre
    2. Você faz login no Mercado Livre
    3. Cookies são salvos em ./ml_browser_data/
    4. Você copia essa pasta para a VPS
    
    """)
    print("="*60)
    
    input("\n⏳ Pressione ENTER para abrir o navegador...")
    
    # headless=False para ver o navegador
    async with ScraperMLAfiliado(
        headless=False,
        wait_ms=2000,
        max_produtos=5
    ) as scraper:
        
        # Verifica se já está logado
        ja_logado = await scraper.verificar_login()
        
        if ja_logado:
            print("\n✅ Você JÁ está logado!")
            print("   Cookies anteriores ainda são válidos.")
            
            refazer = input("\nDeseja refazer o login? (s/N): ").lower()
            if refazer != 's':
                await exportar_cookies()
                return True
        
        # Faz login manual
        sucesso = await scraper.fazer_login_manual()
        
        if sucesso:
            await exportar_cookies()
            return True
        else:
            print("\n❌ Falha no login. Tente novamente.")
            return False


async def exportar_cookies():
    """Empacota os cookies para transferir para VPS"""
    
    if not os.path.exists(BROWSER_DATA_DIR):
        print(f"❌ Pasta {BROWSER_DATA_DIR} não encontrada!")
        return
    
    print("\n📦 Empacotando cookies para VPS...")
    
    # Cria arquivo tar.gz
    import tarfile
    with tarfile.open(EXPORT_ZIP, "w:gz") as tar:
        tar.add(BROWSER_DATA_DIR, arcname="ml_browser_data")
    
    tamanho = os.path.getsize(EXPORT_ZIP) / 1024 / 1024
    
    print(f"""
    
{"="*60}
✅ COOKIES EXPORTADOS COM SUCESSO!
{"="*60}

Arquivo criado: {EXPORT_ZIP} ({tamanho:.1f} MB)

PRÓXIMOS PASSOS:
{"="*60}

1. COPIE O ARQUIVO PARA SUA VPS:

   scp {EXPORT_ZIP} usuario@sua-vps:/caminho/do/scraper/

2. NA VPS, EXTRAIA OS COOKIES:

   cd /caminho/do/scraper
   tar -xzf {EXPORT_ZIP}

3. VERIFIQUE SE A PASTA EXISTE:

   ls -la ml_browser_data/

4. RODE O SCRAPER (vai usar os cookies):

   python scraper_ml_afiliado.py
   # ou
   uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000

{"="*60}

⚠️  IMPORTANTE:
- Os cookies expiram eventualmente (1-7 dias)
- Se parar de funcionar, repita este processo
- Mantenha o arquivo {EXPORT_ZIP} em local seguro

{"="*60}
    """)


async def verificar_cookies_vps():
    """
    Verifica se os cookies importados funcionam.
    Use este comando NA VPS após importar.
    """
    print("\n🔍 Verificando cookies na VPS...")
    
    if not os.path.exists(BROWSER_DATA_DIR):
        print(f"""
❌ Pasta {BROWSER_DATA_DIR} não encontrada!

Você precisa:
1. Rodar 'python login_vps.py' na sua máquina local
2. Copiar o arquivo {EXPORT_ZIP} para a VPS
3. Extrair: tar -xzf {EXPORT_ZIP}
        """)
        return False
    
    # Testa em headless (como vai rodar na VPS)
    async with ScraperMLAfiliado(
        headless=True,  # VPS não tem tela
        wait_ms=2000,
        max_produtos=1
    ) as scraper:
        
        logado = await scraper.verificar_login()
        
        if logado:
            print("""
✅ COOKIES VÁLIDOS!

O scraper está pronto para usar na VPS.
Rode:
  uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000
            """)
            return True
        else:
            print("""
❌ COOKIES INVÁLIDOS OU EXPIRADOS!

Você precisa:
1. Rodar 'python login_vps.py' na sua máquina local novamente
2. Copiar o novo arquivo para a VPS
3. Extrair novamente
            """)
            return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verificar":
        # Modo verificação (para VPS)
        asyncio.run(verificar_cookies_vps())
    else:
        # Modo login (para máquina local)
        asyncio.run(fazer_login_e_exportar())
