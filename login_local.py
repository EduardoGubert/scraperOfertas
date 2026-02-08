#!/usr/bin/env python3
"""
Login Local para Mercado Livre Afiliado
========================================

Este script faz login no ML e salva os cookies para uso na VPS.

Uso:
    python login_local.py           # Faz login e exporta cookies
    python login_local.py --status  # Mostra status dos cookies
    python login_local.py --export  # Apenas exporta (sem login)

Apos o login:
    ./sync_to_vps.ps1   (Windows)
    ./sync_to_vps.sh    (Linux/Mac)
"""

import asyncio
import tarfile
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from scraper_ml_afiliado import ScraperMLAfiliado


# Configuracoes
BROWSER_DATA_DIR = "./ml_browser_data"
EXPORT_FILE = "ml_cookies_export.tar.gz"
METADATA_FILE = f"{BROWSER_DATA_DIR}/login_metadata.json"


def save_metadata():
    """Salva metadata sobre quando o login foi feito"""
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
    metadata = {
        "login_date": datetime.now().isoformat(),
        "expires_estimate": (datetime.now() + timedelta(days=7)).isoformat(),
        "version": "3.0"
    }
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[OK] Metadata salvo em {METADATA_FILE}")


def get_status() -> dict:
    """Retorna status dos cookies"""
    if not os.path.exists(METADATA_FILE):
        return {"exists": False, "message": "Nenhum login encontrado"}

    try:
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)

        login_date = datetime.fromisoformat(metadata["login_date"])
        expires_date = datetime.fromisoformat(metadata["expires_estimate"])
        days_since = (datetime.now() - login_date).days
        days_until = (expires_date - datetime.now()).days

        return {
            "exists": True,
            "login_date": login_date.strftime("%d/%m/%Y %H:%M"),
            "days_since_login": days_since,
            "days_until_expiry": days_until,
            "expired": days_until <= 0
        }
    except Exception as e:
        return {"exists": False, "error": str(e)}


def export_cookies():
    """Exporta cookies para arquivo tar.gz"""
    if not os.path.exists(BROWSER_DATA_DIR):
        print(f"[ERRO] Pasta {BROWSER_DATA_DIR} nao encontrada!")
        print("       Faca login primeiro: python login_local.py")
        return False

    print("\n[...] Exportando cookies...")

    with tarfile.open(EXPORT_FILE, "w:gz") as tar:
        tar.add(BROWSER_DATA_DIR, arcname="ml_browser_data")

    size_mb = os.path.getsize(EXPORT_FILE) / 1024 / 1024
    print(f"[OK] Arquivo criado: {EXPORT_FILE} ({size_mb:.1f} MB)")

    print(f"""
{'='*60}
PROXIMO PASSO: Enviar para VPS
{'='*60}

Windows (PowerShell):
    .\\sync_to_vps.ps1

Linux/Mac:
    ./sync_to_vps.sh

Ou manualmente:
    scp {EXPORT_FILE} root@SUA_VPS:/root/scraperOfertas/
    ssh root@SUA_VPS "cd /root/scraperOfertas && tar -xzf {EXPORT_FILE}"

{'='*60}
""")
    return True


async def do_login():
    """Executa o fluxo de login"""
    print(f"""
{'='*60}
LOGIN - MERCADO LIVRE AFILIADO
{'='*60}

1. Um navegador vai abrir
2. Faca login com sua conta de AFILIADO
3. Apos logar, volte aqui e pressione ENTER
4. Os cookies serao salvos automaticamente

{'='*60}
""")

    # Verifica status atual
    status = get_status()
    if status.get("exists") and not status.get("expired"):
        print(f"[INFO] Login existente encontrado:")
        print(f"       Data: {status['login_date']}")
        print(f"       Expira em: {status['days_until_expiry']} dias")
        response = input("\nDeseja fazer login novamente? (s/N): ").lower()
        if response != 's':
            print("\n[OK] Usando login existente")
            export_cookies()
            return True

    input("Pressione ENTER para abrir o navegador...")

    async with ScraperMLAfiliado(
        headless=False,
        wait_ms=2000,
        max_produtos=1
    ) as scraper:

        # Abre pagina do ML
        await scraper.page.goto("https://www.mercadolivre.com.br")

        # Aguarda login manual
        input("\n[AGUARDANDO] Faca login no navegador e pressione ENTER...")

        # Verifica se logou
        is_logged = await scraper.verificar_login()

        if is_logged:
            print("\n[OK] Login detectado!")
            # Salva metadata ANTES de fechar
            save_metadata()
            # scraper.close() será chamado automaticamente pelo async with
            print("[OK] Cookies salvos com sucesso!")
            # Agora exporta
            export_cookies()
            return True
        else:
            print("\n[ERRO] Login nao detectado!")
            print("       Certifique-se de logar com conta de AFILIADO")
            return False


def show_status():
    """Mostra status dos cookies"""
    print(f"\n{'='*60}")
    print("STATUS DOS COOKIES")
    print(f"{'='*60}\n")

    status = get_status()

    if not status.get("exists"):
        print("[X] Nenhum login encontrado")
        print("    Execute: python login_local.py")
        return

    if status.get("expired"):
        print("[X] Cookies EXPIRADOS!")
    else:
        print("[OK] Cookies validos")

    print(f"""
    Login em:     {status.get('login_date', 'N/A')}
    Dias atras:   {status.get('days_since_login', 'N/A')}
    Expira em:    {status.get('days_until_expiry', 'N/A')} dias
""")

    if os.path.exists(EXPORT_FILE):
        modified = datetime.fromtimestamp(os.path.getmtime(EXPORT_FILE))
        size_mb = os.path.getsize(EXPORT_FILE) / 1024 / 1024
        print(f"    Arquivo:    {EXPORT_FILE} ({size_mb:.1f} MB)")
        print(f"    Atualizado: {modified.strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--status":
            show_status()
        elif cmd == "--export":            
            export_cookies()
        else:
            print(f"Comando desconhecido: {cmd}")
            print("\nUso:")
            print("  python login_local.py           # Faz login")
            print("  python login_local.py --status  # Mostra status")
            print("  python login_local.py --export  # Exporta cookies")
    else:
        asyncio.run(do_login())
