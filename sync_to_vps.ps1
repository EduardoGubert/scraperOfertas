# ============================================
# SYNC COOKIES PARA VPS - Windows PowerShell
# ============================================
# 
# Este script:
# 1. Compacta a pasta ml_browser_data/
# 2. Envia para a VPS via SCP
# 3. Extrai e configura na VPS
#
# Uso:
#   .\sync_to_vps.ps1
#
# ============================================

# CONFIGURAÇÕES - ALTERE AQUI!
$VPS_USER = "root"                    # Usuário SSH da VPS
$VPS_HOST = "seu-ip-ou-dominio"       # IP ou domínio da VPS
$VPS_PATH = "/opt/scraper-ml"         # Caminho na VPS
$SSH_KEY = ""                         # Caminho da chave SSH (opcional, ex: "~/.ssh/id_rsa")

# ============================================

$COOKIES_DIR = "ml_browser_data"
$ZIP_FILE = "ml_cookies_export.zip"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SYNC COOKIES PARA VPS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verifica se a pasta existe
if (-not (Test-Path $COOKIES_DIR)) {
    Write-Host "❌ Pasta $COOKIES_DIR não encontrada!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Você precisa fazer login primeiro:" -ForegroundColor Yellow
    Write-Host "  python login_manual.py" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Verifica configurações
if ($VPS_HOST -eq "seu-ip-ou-dominio") {
    Write-Host "⚠️  CONFIGURE O SCRIPT PRIMEIRO!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Abra o arquivo sync_to_vps.ps1 e altere:" -ForegroundColor White
    Write-Host '  $VPS_USER = "seu-usuario"' -ForegroundColor Gray
    Write-Host '  $VPS_HOST = "seu-ip-da-vps"' -ForegroundColor Gray
    Write-Host '  $VPS_PATH = "/caminho/na/vps"' -ForegroundColor Gray
    Write-Host ""
    
    $VPS_HOST = Read-Host "Ou digite o IP/domínio da VPS agora"
    $VPS_USER = Read-Host "Digite o usuário SSH"
    $VPS_PATH = Read-Host "Digite o caminho na VPS (ex: /opt/scraper-ml)"
}

Write-Host "📦 Compactando cookies..." -ForegroundColor Yellow

# Remove zip antigo se existir
if (Test-Path $ZIP_FILE) {
    Remove-Item $ZIP_FILE -Force
}

# Compacta
Compress-Archive -Path $COOKIES_DIR -DestinationPath $ZIP_FILE -Force

$size = (Get-Item $ZIP_FILE).Length / 1MB
Write-Host "✅ Arquivo criado: $ZIP_FILE ($([math]::Round($size, 2)) MB)" -ForegroundColor Green

Write-Host ""
Write-Host "📤 Enviando para VPS ($VPS_USER@$VPS_HOST)..." -ForegroundColor Yellow

# Monta comando SCP
$scp_cmd = "scp"
if ($SSH_KEY -ne "") {
    $scp_cmd += " -i `"$SSH_KEY`""
}
$scp_cmd += " `"$ZIP_FILE`" `"${VPS_USER}@${VPS_HOST}:${VPS_PATH}/`""

# Executa SCP
try {
    Invoke-Expression $scp_cmd
    if ($LASTEXITCODE -ne 0) { throw "SCP falhou" }
    Write-Host "✅ Arquivo enviado!" -ForegroundColor Green
} catch {
    Write-Host "❌ Erro ao enviar arquivo!" -ForegroundColor Red
    Write-Host "Verifique:" -ForegroundColor Yellow
    Write-Host "  - IP/domínio da VPS está correto?" -ForegroundColor White
    Write-Host "  - Usuário SSH está correto?" -ForegroundColor White
    Write-Host "  - Chave SSH está configurada?" -ForegroundColor White
    Write-Host ""
    Write-Host "Comando executado:" -ForegroundColor Gray
    Write-Host "  $scp_cmd" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "🔧 Configurando na VPS..." -ForegroundColor Yellow

# Monta comando SSH
$ssh_cmd = "ssh"
if ($SSH_KEY -ne "") {
    $ssh_cmd += " -i `"$SSH_KEY`""
}

$remote_commands = @"
cd $VPS_PATH && \
rm -rf ml_browser_data.bak && \
mv ml_browser_data ml_browser_data.bak 2>/dev/null; \
unzip -o ml_cookies_export.zip && \
chmod -R 755 ml_browser_data && \
echo 'Cookies extraidos com sucesso!'
"@

$ssh_full = "$ssh_cmd ${VPS_USER}@${VPS_HOST} `"$remote_commands`""

try {
    Invoke-Expression $ssh_full
    Write-Host "✅ Cookies configurados na VPS!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Não foi possível configurar automaticamente." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Execute manualmente na VPS:" -ForegroundColor White
    Write-Host "  cd $VPS_PATH" -ForegroundColor Gray
    Write-Host "  unzip -o ml_cookies_export.zip" -ForegroundColor Gray
    Write-Host ""
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  ✅ SYNC CONCLUÍDO!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos passos na VPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # Verificar cookies:" -ForegroundColor White
Write-Host "  python login_vps.py --verificar" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Rodar o scraper:" -ForegroundColor White
Write-Host "  python scraper_ml_afiliado.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Ou rodar a API:" -ForegroundColor White
Write-Host "  uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Ou com Docker:" -ForegroundColor White
Write-Host "  docker-compose up -d" -ForegroundColor Gray
Write-Host ""
