#!/usr/bin/env pwsh
# Sincroniza cookies do login local para o container (apenas reinicia)

Write-Host "`n🔄 SINCRONIZAÇÃO DE COOKIES - Local → Container" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Gray

$LOCAL_COOKIES = ".\ml_browser_data"
$CONTAINER_NAME = "egn_scraper_local"

# Verifica se cookies locais existem
if (-not (Test-Path $LOCAL_COOKIES)) {
    Write-Host "`n❌ Cookies locais não encontrados!" -ForegroundColor Red
    Write-Host "   Execute primeiro: python login_local.py" -ForegroundColor Yellow
    exit 1
}

# Verifica arquivos de cookies
$cookieFiles = Get-ChildItem -Path $LOCAL_COOKIES -Recurse -ErrorAction SilentlyContinue | Measure-Object
Write-Host "`n📦 Encontrados $($cookieFiles.Count) arquivos em $LOCAL_COOKIES" -ForegroundColor White

# Verifica se container está rodando
$containerRunning = docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" 2>$null

if (-not $containerRunning) {
    Write-Host "`n⚠️ Container não está rodando!" -ForegroundColor Yellow
    Write-Host "   Inicie com: .\start-local.ps1" -ForegroundColor Yellow
    Write-Host "`n💡 Com bind mount em docker-compose.local.yml, os cookies são compartilhados automaticamente!" -ForegroundColor Green
    Write-Host "   A pasta local ./ml_browser_data é montada diretamente no container." -ForegroundColor Green
    exit 0
}

# Limpa locks do Chrome antes de reiniciar
Write-Host "`n🧹 Removendo locks do Chrome..." -ForegroundColor Yellow
docker exec $CONTAINER_NAME sh -c "rm -f /app/ml_browser_data/SingletonLock /app/ml_browser_data/SingletonSocket /app/ml_browser_data/SingletonCookie" 2>$null

# Container rodando - apenas reinicia para aplicar cookies
Write-Host "`n♻️ Reiniciando container para aplicar cookies..." -ForegroundColor Yellow
docker restart $CONTAINER_NAME

Write-Host "`n⏳ Aguardando container reiniciar..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Verifica saúde do container
$health = docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>$null

if ($health -eq "healthy") {
    Write-Host "`n✅ Container saudável e com cookies sincronizados!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ Container rodando mas health check pendente" -ForegroundColor Yellow
    Write-Host "   Aguarde ~30s e verifique: docker logs $CONTAINER_NAME" -ForegroundColor Gray
}

# Testa autenticação
Write-Host "`n🔐 Testando autenticação no ML..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/auth/status" -Method GET -UseBasicParsing -TimeoutSec 10
    $status = $response.Content | ConvertFrom-Json

    if ($status.cookies_valid) {
        Write-Host "   ✅ Login válido! Expira em $($status.days_until_expiry) dias" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️ Cookies existem mas podem estar expirados" -ForegroundColor Yellow
        Write-Host "   Execute: .\renew-login.ps1" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️ Não foi possível verificar status (API pode estar iniciando)" -ForegroundColor Yellow
}

Write-Host "`n" -ForegroundColor Gray
Write-Host ("="*70) -ForegroundColor Gray
Write-Host "✅ Sincronização concluída!" -ForegroundColor Green
Write-Host ""