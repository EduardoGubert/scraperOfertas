#!/usr/bin/env python3
"""Analisa o HTML do scraper para entender o problema do modal"""

from bs4 import BeautifulSoup
import re
import sys

def analisar_html(filepath):
    print(f"\n{'='*70}")
    print(f"ANALISANDO: {filepath}")
    print(f"{'='*70}\n")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. BUSCA BOTAO COMPARTILHAR
    print("1️⃣  PROCURANDO BOTAO COMPARTILHAR:")
    print("-" * 70)
    
    botoes_compartilhar = soup.find_all('button', string=re.compile('compart', re.I))
    if botoes_compartilhar:
        print(f"✅ Encontrado {len(botoes_compartilhar)} botão(ões):")
        for i, btn in enumerate(botoes_compartilhar[:3], 1):
            print(f"\n   Botão {i}:")
            print(f"   HTML: {str(btn)[:200]}...")
            
            # Verifica atributos
            if btn.get('class'):
                print(f"   Classes: {btn.get('class')}")
            if btn.get('aria-label'):
                print(f"   Aria-label: {btn.get('aria-label')}")
    else:
        print("❌ Botão 'Compartilhar' não encontrado via find_all()")
        
        # Tenta busca case-insensitive no texto bruto
        if 'compartilhar' in html.lower():
            print("⚠️  Mas a palavra existe no HTML (pode estar em maiúscula, minúscula ou accents)")
            
            # Busca contexto
            matches = re.finditer(r'.{0,100}[Cc]ompartilhar.{0,100}', html, re.IGNORECASE)
            for i, m in enumerate(list(matches)[:2], 1):
                print(f"\n   Contexto {i}: ...{m.group()}...")
    
    # 2. BUSCA MODAL DE COMPARTILHAMENTO
    print(f"\n\n2️⃣  PROCURANDO MODAL/INPUTS:")
    print("-" * 70)
    
    # Procura por inputs que possam ter links
    inputs_com_link = soup.find_all('input', value=re.compile('mercadolivre|meli\\.to', re.I))
    if inputs_com_link:
        print(f"✅ Encontrado {len(inputs_com_link)} input(s) com link ML:")
        for i, inp in enumerate(inputs_com_link[:3], 1):
            print(f"\n   Input {i}:")
            print(f"   Value: {inp.get('value', '')[:80]}...")
            print(f"   Type: {inp.get('type', 'N/A')}")
            print(f"   HTML: {str(inp)[:150]}...")
    else:
        print("❌ Nenhum input com link mercadolivre/meli.to encontrado")
        print("   Isso indica que o modal NÃO abriu após o clique")
    
    # 3. BUSCA DIVS COM "Link do produto"
    print(f"\n\n3️⃣  PROCURANDO DIVS COM 'Link do produto':")
    print("-" * 70)
    
    divs_link = soup.find_all('div', string=re.compile('link do produto', re.I))
    if divs_link:
        print(f"✅ Encontrado {len(divs_link)} div(s):")
        for i, div in enumerate(divs_link[:2], 1):
            print(f"\n   Div {i}: {str(div)[:150]}...")
    else:
        print("❌ Nenhuma div com 'Link do produto' encontrada")
    
    # 4. BUSCA POR "Afiliado" ou "affiliate"
    print(f"\n\n4️⃣  PROCURANDO REFERENCIAS A 'AFILIADO':")
    print("-" * 70)
    
    if 'afiliado' in html.lower() or 'affiliate' in html.lower():
        matches = re.finditer(r'.{0,80}afiliado.{0,80}', html, re.IGNORECASE)
        matches_list = list(matches)
        if matches_list:
            print(f"✅ Encontrado {len(matches_list)} menção(ões):")
            for i, m in enumerate(matches_list[:2], 1):
                clean_text = re.sub(r'\s+', ' ', m.group())
                print(f"   {i}. ...{clean_text}...")
        else:
            print("⚠️  Palavra existe mas sem contexto claro")
    else:
        print("❌ Palavra 'afiliado/affiliate' não encontrada")
        print("   ⚠️  ISSO PODE INDICAR QUE O USUARIO NAO É AFILIADO ML!")
    
    # 5. BUSCA PORTAL DE AFILIADOS
    print(f"\n\n5️⃣  VERIFICANDO LINK PARA PORTAL DE AFILIADOS:")
    print("-" * 70)
    
    links_afiliado = soup.find_all('a', href=re.compile('afiliados|affiliate', re.I))
    if links_afiliado:
        print(f"✅ Encontrado {len(links_afiliado)} link(s):")
        for i, link in enumerate(links_afiliado[:3], 1):
            print(f"   {i}. {link.get('href', '')} - {link.get_text()[:40]}")
    else:
        print("❌ Nenhum link para portal de afiliados")
    
    # 6. ESTATISTICAS
    print(f"\n\n6️⃣  ESTATISTICAS DO HTML:")
    print("-" * 70)
    print(f"   • Tamanho: {len(html):,} bytes")
    print(f"   • Total de buttons: {len(soup.find_all('button'))}")
    print(f"   • Total de inputs: {len(soup.find_all('input'))}")
    print(f"   • Total de divs: {len(soup.find_all('div'))}")
    
    print(f"\n{'='*70}")
    print("DIAGNÓSTICO:")
    print(f"{'='*70}")
    
    if not inputs_com_link and not divs_link:
        print("\n🔴 PROBLEMA: Modal de compartilhamento NÃO abriu!")
        print("   Possíveis causas:")
        print("   1. Delay insuficiente após clicar no botão")
        print("   2. Botão errado sendo clicado")
        print("   3. Modal requer ação adicional (ex: login, aceitar termos)")
        print("   4. Usuário não tem permissão de afiliado")
        
        if 'afiliado' not in html.lower():
            print("\n⚠️  PROVÁVEL CAUSA: Conta não é de AFILIADO!")
            print("   • Cadastre-se: https://www.mercadolivre.com.br/afiliados")
    else:
        print("\n🟢 Modal parece ter aberto corretamente!")
        print("   O problema pode estar nos seletores de extração.")
    
    print()

if __name__ == "__main__":
    import os
    
    # Pega o HTML mais recente
    debug_folder = "./debug_container"
    if not os.path.exists(debug_folder):
        print(f"❌ Pasta {debug_folder} não encontrada!")
        sys.exit(1)
    
    htmls = [f for f in os.listdir(debug_folder) if f.endswith('.html')]
    if not htmls:
        print(f"❌ Nenhum HTML encontrado em {debug_folder}!")
        sys.exit(1)
    
    # Analisa os 2 mais recentes
    htmls_sorted = sorted(htmls, reverse=True)
    
    for html_file in htmls_sorted[:2]:
        filepath = os.path.join(debug_folder, html_file)
        analisar_html(filepath)
        print("\n" * 2)
