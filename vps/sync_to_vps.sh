#!/bin/bash
# ============================================
# SYNC COOKIES PARA VPS - Linux/Mac
# ============================================
# 
# Este script:
# 1. Compacta a pasta ml_browser_data/
# 2. Envia para a VPS via SCP
# 3. Extrai e configura na VPS
#
# Uso:
#   chmod +x sync_to_vps.sh
#   ./sync_to_vps.sh
#
# ============================================

# CONFIGURAÇÕES - ALTERE AQUI!
VPS_USER="root"                    # Usuário SSH da VPS
VPS_HOST="seu-ip-ou-dominio"       # IP ou domínio da VPS
VPS_PATH="/opt/scraper-ml"         # Caminho na VPS
SSH_KEY=""                         # Caminho da chave SSH (opcional)

# ============================================

COOKIES_DIR="ml_browser_data"
ZIP_FILE="ml_cookies_export.tar.gz"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  SYNC COOKIES PARA VPS${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Verifica se a pasta existe
if [ ! -d "$COOKIES_DIR" ]; then
    echo -e "${RED}❌ Pasta $COOKIES_DIR não encontrada!${NC}"
    echo ""
    echo -e "${YELLOW}Você precisa fazer login primeiro:${NC}"
    echo "  python login_manual.py"
    echo ""
    exit 1
fi

# Verifica configurações
if [ "$VPS_HOST" = "seu-ip-ou-dominio" ]; then
    echo -e "${YELLOW}⚠️  CONFIGURE O SCRIPT PRIMEIRO!${NC}"
    echo ""
    echo "Abra o arquivo sync_to_vps.sh e altere:"
    echo '  VPS_USER="seu-usuario"'
    echo '  VPS_HOST="seu-ip-da-vps"'
    echo '  VPS_PATH="/caminho/na/vps"'
    echo ""
    
    read -p "Ou digite o IP/domínio da VPS agora: " VPS_HOST
    read -p "Digite o usuário SSH: " VPS_USER
    read -p "Digite o caminho na VPS (ex: /opt/scraper-ml): " VPS_PATH
fi

echo -e "${YELLOW}📦 Compactando cookies...${NC}"

# Remove arquivo antigo se existir
rm -f "$ZIP_FILE"

# Compacta
tar -czf "$ZIP_FILE" "$COOKIES_DIR"

SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo -e "${GREEN}✅ Arquivo criado: $ZIP_FILE ($SIZE)${NC}"

echo ""
echo -e "${YELLOW}📤 Enviando para VPS ($VPS_USER@$VPS_HOST)...${NC}"

# Monta comando SCP
SCP_CMD="scp"
if [ -n "$SSH_KEY" ]; then
    SCP_CMD="$SCP_CMD -i $SSH_KEY"
fi
SCP_CMD="$SCP_CMD $ZIP_FILE ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/"

# Executa SCP
if $SCP_CMD; then
    echo -e "${GREEN}✅ Arquivo enviado!${NC}"
else
    echo -e "${RED}❌ Erro ao enviar arquivo!${NC}"
    echo -e "${YELLOW}Verifique:${NC}"
    echo "  - IP/domínio da VPS está correto?"
    echo "  - Usuário SSH está correto?"
    echo "  - Chave SSH está configurada?"
    exit 1
fi

echo ""
echo -e "${YELLOW}🔧 Configurando na VPS...${NC}"

# Monta comando SSH
SSH_CMD="ssh"
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="$SSH_CMD -i $SSH_KEY"
fi

REMOTE_COMMANDS="cd $VPS_PATH && \
rm -rf ml_browser_data.bak && \
mv ml_browser_data ml_browser_data.bak 2>/dev/null; \
tar -xzf ml_cookies_export.tar.gz && \
chmod -R 755 ml_browser_data && \
echo 'Cookies extraidos com sucesso!'"

if $SSH_CMD "${VPS_USER}@${VPS_HOST}" "$REMOTE_COMMANDS"; then
    echo -e "${GREEN}✅ Cookies configurados na VPS!${NC}"
else
    echo -e "${YELLOW}⚠️  Não foi possível configurar automaticamente.${NC}"
    echo ""
    echo "Execute manualmente na VPS:"
    echo "  cd $VPS_PATH"
    echo "  tar -xzf ml_cookies_export.tar.gz"
    echo ""
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  ✅ SYNC CONCLUÍDO!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}Próximos passos na VPS:${NC}"
echo ""
echo "  # Verificar cookies:"
echo "  python login_vps.py --verificar"
echo ""
echo "  # Rodar o scraper:"
echo "  python scraper_ml_afiliado.py"
echo ""
echo "  # Ou rodar a API:"
echo "  uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000"
echo ""
echo "  # Ou com Docker:"
echo "  docker-compose up -d"
echo ""
