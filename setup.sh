#!/bin/bash
# ============================================
# Setup Scraper ML Afiliado
# ============================================

echo "🚀 Configurando Scraper ML Afiliado..."

# 1. Cria diretório de dados
mkdir -p ml_browser_data
chmod 777 ml_browser_data

# 2. Instala dependências
echo "📦 Instalando dependências Python..."
pip install -r requirements.txt

# 3. Instala Playwright e browsers
echo "🎭 Instalando Playwright..."
playwright install chromium
playwright install-deps chromium

echo ""
echo "✅ Setup concluído!"
echo ""
echo "============================================"
echo "📋 PRÓXIMOS PASSOS:"
echo "============================================"
echo ""
echo "1. FAZER LOGIN (primeira vez):"
echo "   python login_manual.py"
echo ""
echo "2. RODAR A API:"
echo "   uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000"
echo ""
echo "3. TESTAR:"
echo "   curl http://localhost:8000/health"
echo ""
echo "============================================"
