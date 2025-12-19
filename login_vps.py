#!/usr/bin/env python3
"""
==============================================
FLUXO DE LOGIN PARA VPS - VERSÃO MELHORADA
==============================================

ATENÇÃO: Este script SUBSTITUI o login_manual.py quando você usa VPS!

O que faz:
1. ✅ Faz login na sua máquina
2. ✅ Salva cookies localmente (para testar)
3. ✅ Gera arquivo para VPS automaticamente
4. ✅ Mostra instruções claras
5. ✅ Avisa quando cookies estão para expirar

"""

import asyncio
import tarfile
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from scraper_ml_afiliado import ScraperMLAfiliado


# Configurações
BROWSER_DATA_DIR = "./ml_browser_data"
EXPORT_ZIP = "ml_cookies_export.tar.gz"
METADATA_FILE = "./ml_browser_data/login_metadata.json"


async def salvar_metadata():
    """Salva informações sobre quando o login foi feito"""
    metadata = {
        "login_date": datetime.now().isoformat(),
        "expires_estimate": (datetime.now() + timedelta(days=7)).isoformat(),
        "warning_date": (datetime.now() + timedelta(days=5)).isoformat(),
        "version": "2.0"
    }
    
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)


def verificar_expiracao():
    """Verifica se os cookies estão para expirar"""
    if not os.path.exists(METADATA_FILE):
        return None, "Nenhum login encontrado"
    
    try:
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
        
        login_date = datetime.fromisoformat(metadata["login_date"])
        warning_date = datetime.fromisoformat(metadata["warning_date"])
        expires_date = datetime.fromisoformat(metadata["expires_estimate"])
        
        dias_desde_login = (datetime.now() - login_date).days
        dias_ate_expiracao = (expires_date - datetime.now()).days
        
        status = {
            "login_date": login_date.strftime("%d/%m/%Y %H:%M"),
            "dias_desde_login": dias_desde_login,
            "dias_ate_expiracao": dias_ate_expiracao,
            "precisa_refazer": dias_ate_expiracao <= 0
        }
        
        return status, None
        
    except Exception as e:
        return None, f"Erro ao verificar: {str(e)}"


async def fazer_login_e_exportar():
    """Faz login manual e prepara para exportar para VPS"""
    
    print("\n" + "="*70)
    print("🔐 LOGIN PARA VPS - MERCADO LIVRE AFILIADO v2.0")
    print("="*70)
    
    # Verifica se já existe login
    status, erro = verificar_expiracao()
    
    if status and not erro:
        print(f"""
📊 STATUS DO LOGIN ATUAL:
{"="*70}
Login feito em: {status['login_date']}
Dias desde login: {status['dias_desde_login']} dias
Dias até expiração: {status['dias_ate_expiracao']} dias
Status: {'⚠️  EXPIRADO! Precisa fazer novo login' if status['precisa_refazer'] else '✅ Ainda válido'}
{"="*70}
        """)
        
        if not status['precisa_refazer']:
            refazer = input("\n❓ Deseja fazer login novamente? (s/N): ").lower()
            if refazer != 's':
                print("\n✅ Usando login existente...")
                await exportar_cookies()
                return True
    
    print("""
📋 INSTRUÇÕES:
{"="*70}
1. Um navegador vai abrir
2. Faça login com sua conta de AFILIADO do Mercado Livre
3. Após logar, volte aqui e pressione ENTER
4. Os cookies serão salvos AUTOMATICAMENTE para você E para VPS

⚠️  IMPORTANTE: Use a conta de AFILIADO, não a conta comum!
{"="*70}
    """)
    
    input("⏳ Pressione ENTER para abrir o navegador...")
    
    # Faz login
    async with ScraperMLAfiliado(
        headless=False,
        wait_ms=2000,
        max_produtos=5
    ) as scraper:
        
        sucesso = await scraper.fazer_login_manual()
        
        if sucesso:
            # Salva metadata
            await salvar_metadata()
            
            # Exporta automaticamente
            await exportar_cookies()
            
            print("\n" + "="*70)
            print("✅ TUDO PRONTO!")
            print("="*70)
            print("""
Você pode agora:

🖥️  USAR LOCALMENTE:
   python scraper_ml_afiliado.py
   # ou
   uvicorn api_ml_afiliado:app --reload

🚀 ENVIAR PARA VPS:
   Siga as instruções acima para copiar o arquivo .tar.gz
            """)
            return True
        else:
            print("\n❌ Falha no login. Tente novamente.")
            return False


async def exportar_cookies():
    """Empacota os cookies para transferir para VPS"""
    
    if not os.path.exists(BROWSER_DATA_DIR):
        print(f"❌ Pasta {BROWSER_DATA_DIR} não encontrada!")
        return
    
    print("\n📦 Preparando cookies para VPS...")
    
    # Cria arquivo tar.gz
    with tarfile.open(EXPORT_ZIP, "w:gz") as tar:
        tar.add(BROWSER_DATA_DIR, arcname="ml_browser_data")
    
    tamanho = os.path.getsize(EXPORT_ZIP) / 1024 / 1024
    
    print(f"""
{"="*70}
✅ COOKIES EXPORTADOS COM SUCESSO!
{"="*70}

📦 Arquivo: {EXPORT_ZIP} ({tamanho:.1f} MB)

🚀 PARA ENVIAR PARA VPS:
{"="*70}

1️⃣  COPIE O ARQUIVO:
   
   scp {EXPORT_ZIP} usuario@sua-vps:/caminho/do/scraper/

2️⃣  NA VPS, EXTRAIA:
   
   cd /caminho/do/scraper
   tar -xzf {EXPORT_ZIP}
   ls -la ml_browser_data/

3️⃣  VERIFIQUE SE FUNCIONOU NA VPS:
   
   python login_vps.py --verificar

4️⃣  RODE A API NA VPS:
   
   uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000

{"="*70}

⚠️  IMPORTANTE:
- Cookies expiram em ~7 dias
- Este script vai AVISAR quando estiver perto de expirar
- Execute novamente quando necessário

🔔 DICA: Rode 'python login_vps.py --status' para verificar validade
{"="*70}
    """)


async def verificar_cookies_vps():
    """Verifica se os cookies importados funcionam na VPS"""
    
    print("\n🔍 Verificando cookies na VPS...")
    print("="*70)
    
    if not os.path.exists(BROWSER_DATA_DIR):
        print(f"""
❌ Pasta {BROWSER_DATA_DIR} não encontrada!

SOLUÇÃO:
1. Na sua máquina local: python login_vps.py
2. Copie o arquivo: scp {EXPORT_ZIP} usuario@vps:/caminho/
3. Na VPS: tar -xzf {EXPORT_ZIP}
4. Rode novamente: python login_vps.py --verificar
        """)
        return False
    
    # Verifica metadata
    status, erro = verificar_expiracao()
    if status:
        print(f"""
📊 INFORMAÇÕES DOS COOKIES:
Login feito em: {status['login_date']}
Idade: {status['dias_desde_login']} dias
Expiração estimada: {status['dias_ate_expiracao']} dias
        """)
    
    # Testa em headless
    print("\n🧪 Testando login em modo headless (VPS)...")
    
    async with ScraperMLAfiliado(
        headless=True,
        wait_ms=2000,
        max_produtos=1
    ) as scraper:
        
        logado = await scraper.verificar_login()
        
        if logado:
            print("""
✅ COOKIES VÁLIDOS!

O scraper está pronto para rodar na VPS em modo headless.

Você pode iniciar a API:
  uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000
            """)
            return True
        else:
            print("""
❌ COOKIES INVÁLIDOS OU EXPIRADOS!

SOLUÇÃO:
1. Na sua máquina local: python login_vps.py
2. Copie novamente o arquivo para VPS
3. Extraia novamente: tar -xzf {EXPORT_ZIP}
            """)
            return False


async def mostrar_status():
    """Mostra o status atual dos cookies"""
    print("\n📊 STATUS DOS COOKIES")
    print("="*70)
    
    status, erro = verificar_expiracao()
    
    if erro:
        print(f"❌ {erro}")
        print("\n💡 Execute 'python login_vps.py' para fazer o primeiro login")
    else:
        emoji = "✅" if not status['precisa_refazer'] else "❌"
        print(f"""
{emoji} Login feito em: {status['login_date']}
📅 Idade: {status['dias_desde_login']} dias
⏰ Dias restantes: {status['dias_ate_expiracao']} dias

{'⚠️  ATENÇÃO: Cookies expirados! Execute o script novamente.' if status['precisa_refazer'] else ''}
{'⚠️  AVISO: Cookies perto de expirar! Considere fazer novo login.' if 0 < status['dias_ate_expiracao'] <= 2 else ''}
        """)
    
    # Verifica se arquivo de exportação existe
    if os.path.exists(EXPORT_ZIP):
        tamanho = os.path.getsize(EXPORT_ZIP) / 1024 / 1024
        modificado = datetime.fromtimestamp(os.path.getmtime(EXPORT_ZIP))
        print(f"""
📦 Arquivo VPS: {EXPORT_ZIP}
   Tamanho: {tamanho:.1f} MB
   Atualizado: {modificado.strftime("%d/%m/%Y %H:%M")}
        """)
    else:
        print(f"\n⚠️  Arquivo {EXPORT_ZIP} não encontrado. Execute o script para gerar.")
    
    print("="*70)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == "--verificar":
            # Modo verificação (para VPS)
            asyncio.run(verificar_cookies_vps())
        
        elif comando == "--status":
            # Mostra status dos cookies
            asyncio.run(mostrar_status())
        
        else:
            print(f"❌ Comando desconhecido: {comando}")
            print("\nUso:")
            print("  python login_vps.py           # Fazer login")
            print("  python login_vps.py --status  # Ver status dos cookies")
            print("  python login_vps.py --verificar  # Verificar na VPS")
    else:
        # Modo login (padrão)
        asyncio.run(fazer_login_e_exportar())
