#!/usr/bin/env python3
"""
Script para fazer login manual no Mercado Livre.
Execute este script UMA VEZ para salvar os cookies.

Uso:
    python login_manual.py
"""

import asyncio
from scraper_ml_afiliado import ScraperMLAfiliado


async def main():
    print("\n" + "="*60)
    print("🔐 LOGIN MANUAL - MERCADO LIVRE AFILIADO")
    print("="*60)
    print("""
Este script vai:
1. Abrir o navegador
2. Você faz login manualmente
3. Os cookies são salvos automaticamente

IMPORTANTE: 
- O navegador vai abrir em modo visível
- Faça login com sua conta de afiliado
- Após logar, volte aqui e pressione ENTER
    """)
    print("="*60)
    
    input("\nPressione ENTER para abrir o navegador...")
    
    async with ScraperMLAfiliado(
        headless=False,  # IMPORTANTE: Precisa ver o navegador
        wait_ms=1500,
        max_produtos=10
    ) as scraper:
        
        # Verifica se já está logado
        ja_logado = await scraper.verificar_login()
        
        if ja_logado:
            print("\n✅ Você JÁ está logado!")
            print("   Os cookies anteriores ainda são válidos.")
            usar_existente = input("\nDeseja fazer login novamente? (s/N): ").lower()
            if usar_existente != 's':
                print("\n👍 OK! Usando sessão existente.")
                return
        
        # Faz login manual
        sucesso = await scraper.fazer_login_manual()
        
        if sucesso:
            print("\n" + "="*60)
            print("✅ LOGIN SALVO COM SUCESSO!")
            print("="*60)
            print(f"""
Os cookies foram salvos em: {scraper.USER_DATA_DIR}

Agora você pode:
1. Rodar a API: uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000
2. Ou rodar o scraper direto: python scraper_ml_afiliado.py

O login será mantido entre execuções!
            """)
        else:
            print("\n❌ Falha no login. Tente novamente.")


if __name__ == "__main__":
    asyncio.run(main())
