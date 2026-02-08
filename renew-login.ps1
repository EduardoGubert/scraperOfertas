#!/usr/bin/env pwsh
# Renovação automática de login ML (Local → Container)

param(
    [switch]$Auto  # Se -Auto, não pergunta confirmação
)

$ErrorActionPreference = "Stop"

Write-Host "`n🔄 RENOVAÇÃO DE LOGIN - Mercado Livre" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Gray

# Verifica se container está rodando
$containerRunning = docker ps --filter "name=egn_scraper_local" --format "{{.Names}}" 2>$null

if (-not $containerRunning) {
    Write-Host "`n❌ Container não está rodando!" -ForegroundColor Red
    Write-Host "   Inicie com: .\start-local.ps1" -ForegroundColor Yellow
    exit 1
}

# Verifica status atual
Write-Host "`n📊 Verificando status atual dos cookies..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/auth/status" -Method GET -UseBasicParsing -TimeoutSec 10
    $status = $response.Content | ConvertFrom-Json
    
    Write-Host "`n   Cookies existem: " -NoNewline
    if ($status.cookies_exist) {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌" -ForegroundColor Red
    }
    
    Write-Host "   Cookies válidos: " -NoNewline
    if ($status.cookies_valid) {
        Write-Host "✅ (Expiram em $($status.days_until_expiry) dias)" -ForegroundColor Green
    } else {
        Write-Host "❌" -ForegroundColor Red
    }
    
    Write-Host "   Último login: " -NoNewline
    if ($status.login_date) {
        Write-Host "$($status.login_date)" -ForegroundColor White
    } else {
        Write-Host "Nunca" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "`n⚠️ Não foi possível verificar status" -ForegroundColor Yellow
}

# Confirmação
if (-not $Auto) {
    Write-Host "`n❓ Deseja renovar o login agora? (S/N): " -NoNewline -ForegroundColor Yellow
    $confirm = Read-Host
    
    if ($confirm -ne "S" -and $confirm -ne "s") {
        Write-Host "`n❌ Operação cancelada pelo usuário" -ForegroundColor Red
        exit 0
    }
}

# Executa renovação
Write-Host "`n🔐 Iniciando renovação de login..." -ForegroundColor Green
Write-Host ("="*70) -ForegroundColor Gray

Write-Host "`n1️⃣ Executando login local com Playwright..." -ForegroundColor Cyan
python login_local.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Erro ao executar login_local.py" -ForegroundColor Red
    exit 1
}

# Verifica se cookies foram salvos
if (-not (Test-Path ".\ml_browser_data")) {
    Write-Host "`n❌ Cookies não foram salvos!" -ForegroundColor Red
    exit 1
}

$cookieCount = (Get-ChildItem -Path ".\ml_browser_data" -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "`n   ✅ Cookies salvos localmente ($cookieCount arquivos)" -ForegroundColor Green

# Reinicia container para aplicar cookies
Write-Host "`n2️⃣ Reiniciando container para aplicar cookies..." -ForegroundColor Cyan
docker restart egn_scraper_local

Write-Host "`n   ⏳ Aguardando container reiniciar..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# Verifica novo status
Write-Host "`n3️⃣ Verificando novo status..." -ForegroundColor Cyan

$maxAttempts = 6
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/auth/status" -Method GET -UseBasicParsing -TimeoutSec 5
        $newStatus = $response.Content | ConvertFrom-Json
        
        if ($newStatus.cookies_valid) {
            Write-Host "`n   ✅ Login renovado com sucesso!" -ForegroundColor Green
            Write-Host "   📅 Nova data de login: $($newStatus.login_date)" -ForegroundColor White
            Write-Host "   ⏰ Expira em: $($newStatus.days_until_expiry) dias" -ForegroundColor White
            
            Write-Host "`n" -ForegroundColor Gray
            Write-Host ("="*70) -ForegroundColor Gray
            Write-Host "✅ RENOVAÇÃO CONCLUÍDA!" -ForegroundColor Green
            Write-Host ("="*70) -ForegroundColor Gray
            Write-Host ""
            exit 0
        } else {
            Write-Host "   ⚠️ Cookies ainda não estão válidos (tentativa $attempt/$maxAttempts)" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "   ⏳ Aguardando API ficar disponível (tentativa $attempt/$maxAttempts)..." -ForegroundColor Gray
    }
    
    Start-Sleep -Seconds 5
    $attempt++
}

Write-Host "`n⚠️ Container reiniciou mas cookies podem não estar válidos" -ForegroundColor Yellow
Write-Host "   Verifique manualmente: http://localhost:8000/auth/status" -ForegroundColor Gray
Write-Host ""
