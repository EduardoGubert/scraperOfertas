#!/usr/bin/env python3
"""Login local para salvar cookies do Mercado Livre Afiliado."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

from scraper_ml_afiliado import ScraperMLAfiliado


BROWSER_DATA_DIR = "./ml_browser_data"
EXPORT_FILE = "ml_cookies_export.tar.gz"
METADATA_FILE = f"{BROWSER_DATA_DIR}/login_metadata.json"


def save_metadata() -> None:
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
    metadata = {
        "login_date": datetime.now().isoformat(),
        "expires_estimate": (datetime.now() + timedelta(days=7)).isoformat(),
        "version": "4.0",
    }
    Path(METADATA_FILE).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"[OK] Metadata salvo em {METADATA_FILE}")


def get_status() -> dict:
    if not os.path.exists(METADATA_FILE):
        return {"exists": False, "message": "Nenhum login encontrado"}

    try:
        metadata = json.loads(Path(METADATA_FILE).read_text(encoding="utf-8"))
        login_date = datetime.fromisoformat(metadata["login_date"])
        expires_date = datetime.fromisoformat(metadata["expires_estimate"])
        days_since = (datetime.now() - login_date).days
        days_until = (expires_date - datetime.now()).days

        return {
            "exists": True,
            "login_date": login_date.strftime("%d/%m/%Y %H:%M"),
            "days_since_login": days_since,
            "days_until_expiry": days_until,
            "expired": days_until <= 0,
        }
    except Exception as exc:
        return {"exists": False, "error": str(exc)}


def export_cookies() -> bool:
    if not os.path.exists(BROWSER_DATA_DIR):
        print(f"[ERRO] Pasta {BROWSER_DATA_DIR} nao encontrada")
        print("       Faca login primeiro: python login_local.py")
        return False

    print("\n[...] Exportando cookies...")
    with tarfile.open(EXPORT_FILE, "w:gz") as tar:
        tar.add(BROWSER_DATA_DIR, arcname="ml_browser_data")

    size_mb = os.path.getsize(EXPORT_FILE) / 1024 / 1024
    print(f"[OK] Arquivo criado: {EXPORT_FILE} ({size_mb:.1f} MB)")
    return True


async def do_login() -> bool:
    status = get_status()
    if status.get("exists") and not status.get("expired"):
        print("[INFO] Login existente encontrado")
        print(f"       Data: {status['login_date']}")
        print(f"       Expira em: {status['days_until_expiry']} dias")
        response = input("Deseja fazer login novamente? (s/N): ").strip().lower()
        if response != "s":
            print("[OK] Mantendo login existente")
            return export_cookies()

    input("Pressione ENTER para abrir o navegador...")

    async with ScraperMLAfiliado(headless=False, wait_ms=1800, max_produtos=1) as scraper:
        ok = await scraper.fazer_login_manual()
        if ok:
            save_metadata()
            print("[OK] Login salvo com sucesso")
            return export_cookies()

        print("[ERRO] Login nao detectado")
        return False


def show_status() -> None:
    status = get_status()
    print("\n" + "=" * 60)
    print("STATUS DOS COOKIES")
    print("=" * 60)

    if not status.get("exists"):
        print("[X] Nenhum login encontrado")
        print("    Execute: python login_local.py")
        return

    if status.get("expired"):
        print("[X] Cookies expirados")
    else:
        print("[OK] Cookies validos")

    print(f"Login em: {status.get('login_date')}")
    print(f"Dias atras: {status.get('days_since_login')}")
    print(f"Expira em: {status.get('days_until_expiry')} dias")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--status":
            show_status()
        elif cmd == "--export":
            export_cookies()
        else:
            print(f"Comando desconhecido: {cmd}")
            print("Uso: python login_local.py [--status|--export]")
    else:
        asyncio.run(do_login())
