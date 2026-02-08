#!/usr/bin/env pwsh
# Diagnóstico do ambiente local

Write-Host "`n🔍 DIAGNÓSTICO - Ambiente Local" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Gray

# 1. Status dos containers
Write-Host "`n📦 Status dos containers:" -ForegroundColor Yellow
docker ps -a --filter "name=egn_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. Logs do Scraper (últimas 50 linhas)
Write-Host "`n📋 Logs do Scraper (últimas 50 linhas):" -ForegroundColor Yellow
Write-Host ("="*70) -ForegroundColor Gray
docker logs egn_scraper_local --tail 50 2>&1

# 3. Logs do PostgreSQL (últimas 20 linhas)
Write-Host "`n📋 Logs do PostgreSQL (últimas 20 linhas):" -ForegroundColor Yellow
Write-Host ("="*70) -ForegroundColor Gray
docker logs egn_postgres_local --tail 20 2>&1

# 4. Logs do n8n (últimas 20 linhas)
Write-Host "`n📋 Logs do n8n (últimas 20 linhas):" -ForegroundColor Yellow
Write-Host ("="*70) -ForegroundColor Gray
docker logs egn_n8n_local --tail 20 2>&1

# 5. Teste de conectividade
Write-Host "`n🌐 Testes de conectividade:" -ForegroundColor Yellow

Write-Host "   PostgreSQL (5432)... " -NoNewline
try {
    $result = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($result.TcpTestSucceeded) {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌" -ForegroundColor Red
    }
} catch {
    Write-Host "❌" -ForegroundColor Red
}

Write-Host "   n8n (5678)... " -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5678" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
    Write-Host "✅" -ForegroundColor Green
} catch {
    Write-Host "❌" -ForegroundColor Red
}

Write-Host "   Scraper (8000)... " -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
    Write-Host "✅" -ForegroundColor Green
} catch {
    Write-Host "❌" -ForegroundColor Red
}

# 6. Verifica volumes
Write-Host "`n💾 Volumes Docker:" -ForegroundColor Yellow
docker volume ls --filter "name=scraperofertas_"

# 7. Status dos cookies
Write-Host "`n🍪 Status dos Cookies:" -ForegroundColor Yellow
if (Test-Path ".\ml_browser_data") {
    $cookieCount = (Get-ChildItem -Path ".\ml_browser_data" -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "   Arquivos locais: $cookieCount" -ForegroundColor White
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/auth/status" -UseBasicParsing -TimeoutSec 5
        $status = $response.Content | ConvertFrom-Json
        
        Write-Host "   Cookies válidos: " -NoNewline
        if ($status.cookies_valid) {
            Write-Host "✅ (Expiram em $($status.days_until_expiry) dias)" -ForegroundColor Green
        } else {
            Write-Host "❌" -ForegroundColor Red
        }
    } catch {
        Write-Host "   API não respondeu" -ForegroundColor Gray
    }
} else {
    Write-Host "   ❌ Pasta ml_browser_data não existe" -ForegroundColor Red
}

Write-Host "`n" -ForegroundColor Gray
Write-Host ("="*70) -ForegroundColor Gray
Write-Host "✅ Diagnóstico concluído!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 DICAS:" -ForegroundColor Cyan
Write-Host "   • Ver logs em tempo real: docker logs -f egn_scraper_local" -ForegroundColor Gray
Write-Host "   • Renovar login: .\renew-login.ps1" -ForegroundColor Gray
Write-Host "   • Parar tudo: .\stop-local.ps1" -ForegroundColor Gray
Write-Host ""
