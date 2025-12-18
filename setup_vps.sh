#!/bin/bash
# ============================================
# SETUP VPS - Scraper ML Afiliado
# ============================================
#
# Este script configura tudo na VPS:
# 1. Instala dependências
# 2. Extrai cookies (se existirem)
# 3. Verifica login
# 4. Inicia o serviço
#
# Uso:
#   chmod +x setup_vps.sh
#   ./setup_vps.sh
#
# ============================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  SETUP VPS - SCRAPER ML AFILIADO${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ============================================
# 1. VERIFICA PYTHON
# ============================================
echo -e "${YELLOW}1. Verificando Python...${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python3 não encontrado!${NC}"
    echo "Instalando..."
    apt update && apt install -y python3 python3-pip
fi

# ============================================
# 2. INSTALA DEPENDÊNCIAS
# ============================================
echo ""
echo -e "${YELLOW}2. Instalando dependências Python...${NC}"

pip3 install -r requirements.txt --quiet

echo -e "${GREEN}✅ Dependências instaladas${NC}"

# ============================================
# 3. INSTALA PLAYWRIGHT
# ============================================
echo ""
echo -e "${YELLOW}3. Instalando Playwright...${NC}"

# Instala dependências do sistema para Playwright
apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    --no-install-recommends 2>/dev/null || true

# Instala Playwright
python3 -m playwright install chromium --with-deps 2>/dev/null || \
python3 -m playwright install chromium

echo -e "${GREEN}✅ Playwright instalado${NC}"

# ============================================
# 4. EXTRAI COOKIES (se existirem)
# ============================================
echo ""
echo -e "${YELLOW}4. Verificando cookies...${NC}"

if [ -f "ml_cookies_export.tar.gz" ]; then
    echo "Encontrado ml_cookies_export.tar.gz"
    
    # Backup do antigo
    if [ -d "ml_browser_data" ]; then
        rm -rf ml_browser_data.bak
        mv ml_browser_data ml_browser_data.bak
    fi
    
    # Extrai
    tar -xzf ml_cookies_export.tar.gz
    chmod -R 755 ml_browser_data
    
    echo -e "${GREEN}✅ Cookies extraídos${NC}"
    
elif [ -f "ml_cookies_export.zip" ]; then
    echo "Encontrado ml_cookies_export.zip"
    
    # Backup do antigo
    if [ -d "ml_browser_data" ]; then
        rm -rf ml_browser_data.bak
        mv ml_browser_data ml_browser_data.bak
    fi
    
    # Extrai
    unzip -o ml_cookies_export.zip
    chmod -R 755 ml_browser_data
    
    echo -e "${GREEN}✅ Cookies extraídos${NC}"
    
elif [ -d "ml_browser_data" ]; then
    echo -e "${GREEN}✅ Pasta ml_browser_data já existe${NC}"
    
else
    echo -e "${YELLOW}⚠️  Nenhum cookie encontrado!${NC}"
    echo ""
    echo "Você precisa:"
    echo "1. Na sua máquina local, executar: python login_manual.py"
    echo "2. Depois, executar: ./sync_to_vps.ps1 (Windows) ou ./sync_to_vps.sh (Linux/Mac)"
    echo ""
fi

# ============================================
# 5. VERIFICA LOGIN
# ============================================
echo ""
echo -e "${YELLOW}5. Verificando login...${NC}"

if [ -d "ml_browser_data" ]; then
    python3 login_vps.py --verificar 2>/dev/null || echo -e "${YELLOW}⚠️  Execute manualmente: python3 login_vps.py --verificar${NC}"
else
    echo -e "${YELLOW}⚠️  Pule esta etapa - cookies não disponíveis${NC}"
fi

# ============================================
# 6. RESUMO
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  ✅ SETUP CONCLUÍDO!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Para rodar o scraper:"
echo ""
echo "  # Modo direto:"
echo "  python3 scraper_ml_afiliado.py"
echo ""
echo "  # Modo API:"
echo "  uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000"
echo ""
echo "  # Com Docker:"
echo "  docker-compose up -d"
echo ""

# Verifica se tem cookies válidos
if [ -d "ml_browser_data" ]; then
    echo -e "${GREEN}✅ Pronto para usar!${NC}"
else
    echo -e "${YELLOW}⚠️  Lembre-se de enviar os cookies da sua máquina local!${NC}"
fi
echo ""
