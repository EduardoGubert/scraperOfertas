# Sync cookies to VPS and restart service
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$VPS_USER = "root"
$VPS_HOST = "72.60.51.81"
$VPS_PATH = "/root/scraperOfertas"
$STACK_NAME = "scraperofertas"
$SERVICE_NAME = "${STACK_NAME}_scraper-ml-afiliado"
$EXPORT_FILE = "ml_cookies_export.tar.gz"

if (-not (Test-Path $EXPORT_FILE)) {
    Write-Host "Cookie export not found. Run: python -m apps.scraper.login_local" -ForegroundColor Red
    exit 1
}

scp $EXPORT_FILE "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/"
if ($LASTEXITCODE -ne 0) { exit 1 }

$extractCmd = "cd $VPS_PATH && rm -rf ml_browser_data.bak && mv ml_browser_data ml_browser_data.bak 2>/dev/null; tar -xzf $EXPORT_FILE && chmod -R 755 ml_browser_data"
ssh "${VPS_USER}@${VPS_HOST}" $extractCmd
if ($LASTEXITCODE -ne 0) { exit 1 }

ssh "${VPS_USER}@${VPS_HOST}" "docker service update --force $SERVICE_NAME"

Write-Host "Sync complete." -ForegroundColor Green
