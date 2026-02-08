"""
Script de teste para verificar as otimizações anti-bot

Uso:
    python test_anti_bot.py

Testa:
    1. Chrome Real vs Chromium
    2. Navegação humana
    3. Proxy (se configurado)
"""

import asyncio
import os
from scraper_ml_afiliado import ScraperMLAfiliado


async def test_sem_proxy():
    """Teste básico sem proxy (Chrome real + navegação humana)"""
    print("\n" + "="*70)
    print("🧪 TESTE 1: Chrome Real + Navegação Humana (SEM PROXY)")
    print("="*70)
    
    try:
        async with ScraperMLAfiliado(
            use_chrome=True,  # Chrome real
            headless=False,   # Mostra navegador
            max_produtos=2    # Apenas 2 para teste rápido
        ) as scraper:
            # Tenta buscar ofertas (navegação humana é automática)
            links = await scraper.obter_links_ofertas()
            
            print(f"\n✅ Encontrados {len(links)} produtos")
            
            if links:
                print("\n🧪 Testando 1 produto...")
                produto = await scraper.extrair_dados_produto(links[0])
                
                if produto['status'] == 'sucesso':
                    print(f"✅ SUCESSO!")
                    print(f"   Nome: {produto['nome']}")
                    print(f"   Link: {produto['url_curta']}")
                elif produto['status'] == 'sem_link':
                    print(f"⚠️ Página carregou mas não encontrou link de afiliado")
                    print(f"   Pode ser problema com botão Compartilhar")
                else:
                    print(f"❌ FALHOU: {produto['erro']}")
            
            return len(links) > 0
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def test_com_proxy():
    """Teste com proxy (configure as variáveis de ambiente)"""
    print("\n" + "="*70)
    print("🧪 TESTE 2: Chrome Real + Proxy + Navegação Humana")
    print("="*70)
    
    # Lê configuração do proxy de variáveis de ambiente
    proxy_server = os.getenv('PROXY_SERVER')  # Ex: http://proxy.com:8080
    proxy_user = os.getenv('PROXY_USER')
    proxy_pass = os.getenv('PROXY_PASS')
    
    if not proxy_server:
        print("⚠️ PROXY_SERVER não configurado")
        print("   Configure as variáveis de ambiente:")
        print("   - PROXY_SERVER=http://seu-proxy:porta")
        print("   - PROXY_USER=usuario (opcional)")
        print("   - PROXY_PASS=senha (opcional)")
        return False
    
    proxy_config = {'server': proxy_server}
    if proxy_user:
        proxy_config['username'] = proxy_user
    if proxy_pass:
        proxy_config['password'] = proxy_pass
    
    print(f"🌐 Usando proxy: {proxy_server}")
    
    try:
        async with ScraperMLAfiliado(
            use_chrome=True,
            headless=False,
            proxy=proxy_config,
            max_produtos=2
        ) as scraper:
            # Verifica IP público
            print("\n🔍 Verificando IP do proxy...")
            await scraper.page.goto('https://api.ipify.org?format=json')
            await scraper._human_delay(1000, 2000)
            
            ip_info = await scraper.page.evaluate('() => document.body.textContent')
            print(f"   IP detectado: {ip_info}")
            
            # Testa scraping
            links = await scraper.obter_links_ofertas()
            print(f"\n✅ Encontrados {len(links)} produtos")
            
            if links:
                print("\n🧪 Testando 1 produto...")
                produto = await scraper.extrair_dados_produto(links[0])
                
                if produto['status'] == 'sucesso':
                    print(f"✅ SUCESSO COM PROXY!")
                    print(f"   Nome: {produto['nome']}")
                    print(f"   Link: {produto['url_curta']}")
                elif produto['status'] == 'sem_link':
                    print(f"⚠️ Página carregou mas não encontrou link de afiliado")
                else:
                    print(f"❌ FALHOU: {produto['erro']}")
            
            return len(links) > 0
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def main():
    print("\n" + "🛡️"*35)
    print(" "*15 + "TESTE ANTI-BOT")
    print("🛡️"*35 + "\n")
    
    print("Este script vai testar as 3 otimizações implementadas:")
    print("1. ✅ Chrome Real (menos detectável que Chromium)")
    print("2. ✅ Navegação Humana (visita home, scroll, delays)")
    print("3. ⚠️ Proxy (opcional, configure via env vars)")
    
    # Teste 1: Sem proxy
    resultado1 = await test_sem_proxy()
    
    # Teste 2: Com proxy (se configurado)
    if os.getenv('PROXY_SERVER'):
        await asyncio.sleep(3)  # Pausa entre testes
        resultado2 = await test_com_proxy()
    else:
        print("\n" + "="*70)
        print("ℹ️ TESTE 2 PULADO (proxy não configurado)")
        print("="*70)
        resultado2 = None
    
    # Resumo final
    print("\n" + "="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70)
    print(f"Teste 1 (Sem Proxy):  {'✅ PASSOU' if resultado1 else '❌ FALHOU'}")
    if resultado2 is not None:
        print(f"Teste 2 (Com Proxy):  {'✅ PASSOU' if resultado2 else '❌ FALHOU'}")
    else:
        print(f"Teste 2 (Com Proxy):  ⚠️ Não executado (configure PROXY_SERVER)")
    print("="*70)
    
    if resultado1:
        print("\n🎉 OTIMIZAÇÕES FUNCIONANDO!")
        print("   Próximos passos:")
        print("   1. ✅ Chrome real está ativo")
        print("   2. ✅ Navegação humana funcionando")
        if resultado2 is None:
            print("   3. 🌐 Configure proxy residencial brasileiro para melhor resultado")
            print("      Edite .env ou exporte variáveis:")
            print("      export PROXY_SERVER='http://proxy:porta'")
            print("      export PROXY_USER='usuario'")
            print("      export PROXY_PASS='senha'")
    else:
        print("\n❌ PROBLEMA DETECTADO")
        print("   Verifique:")
        print("   - Chrome está instalado? (necessário para use_chrome=True)")
        print("   - Login foi feito? Execute: python login_local.py")
        print("   - Ainda vendo account-verification? Tente proxy residencial")


if __name__ == "__main__":
    asyncio.run(main())
