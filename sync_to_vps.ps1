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
$VPS_USER = "root"
$VPS_HOST = "72.60.51.81"
$VPS_PATH = "/root/scraper-ml"
$SSH_KEY = ""

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
    Write-Host "ERRO: Pasta $COOKIES_DIR nao encontrada!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Voce precisa fazer login primeiro:" -ForegroundColor Yellow
    Write-Host "  python login_manual.py" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Verifica configurações
if ($VPS_HOST -eq "seu-ip-ou-dominio") {
    Write-Host "AVISO: CONFIGURE O SCRIPT PRIMEIRO!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Abra o arquivo sync_to_vps.ps1 e altere:" -ForegroundColor White
    Write-Host '  $VPS_USER = "seu-usuario"' -ForegroundColor Gray
    Write-Host '  $VPS_HOST = "seu-ip-da-vps"' -ForegroundColor Gray
    Write-Host '  $VPS_PATH = "/caminho/na/vps"' -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "Compactando cookies..." -ForegroundColor Yellow

# Remove zip antigo se existir
if (Test-Path $ZIP_FILE) {
    Remove-Item $ZIP_FILE -Force
}

# Compacta
Compress-Archive -Path $COOKIES_DIR -DestinationPath $ZIP_FILE -Force

$size = (Get-Item $ZIP_FILE).Length / 1MB
$sizeRounded = [math]::Round($size, 2)
Write-Host "OK: Arquivo criado: $ZIP_FILE ($sizeRounded MB)" -ForegroundColor Green

Write-Host ""
Write-Host "Enviando para VPS ($VPS_USER@$VPS_HOST)..." -ForegroundColor Yellow

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
    Write-Host "OK: Arquivo enviado!" -ForegroundColor Green
} catch {
    Write-Host "ERRO: Nao foi possivel enviar arquivo!" -ForegroundColor Red
    Write-Host "Verifique:" -ForegroundColor Yellow
    Write-Host "  - IP/dominio da VPS esta correto?" -ForegroundColor White
    Write-Host "  - Usuario SSH esta correto?" -ForegroundColor White
    Write-Host "  - Pasta existe na VPS?" -ForegroundColor White
    Write-Host ""
    Write-Host "Comando executado:" -ForegroundColor Gray
    Write-Host "  $scp_cmd" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Crie a pasta primeiro na VPS:" -ForegroundColor Yellow
    Write-Host "  ssh $VPS_USER@$VPS_HOST" -ForegroundColor White
    Write-Host "  mkdir -p $VPS_PATH" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Configurando na VPS..." -ForegroundColor Yellow

# Monta comando SSH
$ssh_cmd = "ssh"
if ($SSH_KEY -ne "") {
    $ssh_cmd += " -i `"$SSH_KEY`""
}

$remote_commands = "cd $VPS_PATH; rm -rf ml_browser_data.bak; mv ml_browser_data ml_browser_data.bak 2>/dev/null; unzip -o ml_cookies_export.zip; chmod -R 755 ml_browser_data; echo 'Cookies extraidos com sucesso!'"

$ssh_full = "$ssh_cmd ${VPS_USER}@${VPS_HOST} `"$remote_commands`""

try {
    Invoke-Expression $ssh_full
    Write-Host "OK: Cookies configurados na VPS!" -ForegroundColor Green
} catch {
    Write-Host "AVISO: Nao foi possivel configurar automaticamente." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Execute manualmente na VPS:" -ForegroundColor White
    Write-Host "  ssh $VPS_USER@$VPS_HOST" -ForegroundColor Gray
    Write-Host "  cd $VPS_PATH" -ForegroundColor Gray
    Write-Host "  unzip -o ml_cookies_export.zip" -ForegroundColor Gray
    Write-Host "  chmod -R 755 ml_browser_data" -ForegroundColor Gray
    Write-Host ""
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SYNC CONCLUIDO!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Verificar cookies na VPS:" -ForegroundColor White
Write-Host "   ssh $VPS_USER@$VPS_HOST" -ForegroundColor Gray
Write-Host "   cd $VPS_PATH" -ForegroundColor Gray
Write-Host "   ls -la ml_browser_data/" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Subir o container no Portainer" -ForegroundColor White
Write-Host ""
Write-Host "3. Testar a API:" -ForegroundColor White
Write-Host "   http://$VPS_HOST:8000/docs" -ForegroundColor Gray
Write-Host ""