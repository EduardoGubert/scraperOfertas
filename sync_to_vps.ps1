# ============================================
# SYNC COOKIES PARA VPS
# ============================================
#
# Este script envia os cookies para a VPS e reinicia o servico.
#
# Uso:
#   .\sync_to_vps.ps1
#
# ============================================

# CONFIGURACOES
$VPS_USER = "root"
$VPS_HOST = "72.60.51.81"
$VPS_PATH = "/root/scraperOfertas"
$STACK_NAME = "scraperofertas"
$SERVICE_NAME = "${STACK_NAME}_scraper-ml-afiliado"

# ============================================

$EXPORT_FILE = "ml_cookies_export.tar.gz"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SYNC COOKIES PARA VPS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verifica se arquivo existe
if (-not (Test-Path $EXPORT_FILE)) {
    Write-Host "[ERRO] Arquivo $EXPORT_FILE nao encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Execute primeiro:" -ForegroundColor Yellow
    Write-Host "  python login_local.py" -ForegroundColor White
    Write-Host ""
    exit 1
}

$size = (Get-Item $EXPORT_FILE).Length / 1MB
$sizeRounded = [math]::Round($size, 2)
Write-Host "[1/4] Arquivo encontrado: $EXPORT_FILE ($sizeRounded MB)" -ForegroundColor Green

# Envia arquivo
Write-Host ""
Write-Host "[2/4] Enviando para VPS..." -ForegroundColor Yellow
scp $EXPORT_FILE "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao enviar arquivo!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Arquivo enviado!" -ForegroundColor Green

# Extrai na VPS
Write-Host ""
Write-Host "[3/4] Extraindo cookies na VPS..." -ForegroundColor Yellow
$extract_cmd = "cd $VPS_PATH && rm -rf ml_browser_data.bak && mv ml_browser_data ml_browser_data.bak 2>/dev/null; tar -xzf $EXPORT_FILE && chmod -R 755 ml_browser_data && echo 'OK'"
ssh "${VPS_USER}@${VPS_HOST}" $extract_cmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao extrair!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Cookies extraidos!" -ForegroundColor Green

# Reinicia servico
Write-Host ""
Write-Host "[4/4] Reiniciando servico Docker..." -ForegroundColor Yellow
ssh "${VPS_USER}@${VPS_HOST}" "docker service update --force $SERVICE_NAME"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] Nao foi possivel reiniciar automaticamente" -ForegroundColor Yellow
    Write-Host "        Reinicie manualmente no Portainer" -ForegroundColor White
} else {
    Write-Host "[OK] Servico reiniciado!" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SYNC CONCLUIDO!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Verifique o status:" -ForegroundColor White
Write-Host "  curl -k https://scraperofertas.soluztions.shop/auth/status -H 'X-API-Key: egn-2025-secret-key'" -ForegroundColor Gray
Write-Host ""
