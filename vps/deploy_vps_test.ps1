#!/usr/bin/env pwsh
# Deploy e Teste Automático na VPS
# Uso: .\deploy_vps_test.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n" -NoNewline
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host "  🚀 DEPLOY E TESTE NA VPS - Anti-Bot Otimizado" -ForegroundColor Yellow
Write-Host ("="*70) -ForegroundColor Cyan

# Configurações
$IMAGE_NAME = "eduardogubert/scraperofertas"
$TAG = "latest"
$VPS_HOST = "72.60.51.81"
$VPS_USER = "root"
$VPS_PASS = "B@ruck151022#@"
$SERVICE_NAME = "scraperofertas_scraper-ml-afiliado"

# Função para executar comando SSH
function Invoke-SSHCommand {
    param([string]$Command)
    
    $sshpass = "sshpass"
    if (-not (Get-Command $sshpass -ErrorAction SilentlyContinue)) {
        # Sem sshpass, usa SSH direto (pode pedir senha)
        ssh "${VPS_USER}@${VPS_HOST}" $Command
    } else {
        sshpass -p $VPS_PASS ssh "${VPS_USER}@${VPS_HOST}" $Command
    }
}

Write-Host "`n📦 ETAPA 1: Build da imagem Docker..." -ForegroundColor Green
Write-Host "   Buildando com otimizações anti-bot..." -ForegroundColor Gray

docker build -t "${IMAGE_NAME}:${TAG}" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro no build!" -ForegroundColor Red
    exit 1
}

$IMAGE_ID = docker images -q "${IMAGE_NAME}:${TAG}"
Write-Host "   ✅ Build concluído: ${IMAGE_ID}" -ForegroundColor Green

Write-Host "`n🔼 ETAPA 2: Push para Docker Hub..." -ForegroundColor Green
Write-Host "   Enviando imagem..." -ForegroundColor Gray

docker push "${IMAGE_NAME}:${TAG}"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro no push!" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Push concluído!" -ForegroundColor Green

Write-Host "`n🔄 ETAPA 3: Atualizando serviço na VPS..." -ForegroundColor Green
Write-Host "   Conectando em ${VPS_HOST}..." -ForegroundColor Gray

# Atualiza serviço no Docker Swarm
$updateCmd = "docker service update --image ${IMAGE_NAME}:${TAG} --force ${SERVICE_NAME}"
Invoke-SSHCommand $updateCmd

Write-Host "   ⏳ Aguardando convergência do serviço..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Verifica status
$statusCmd = "docker service ps ${SERVICE_NAME} --filter 'desired-state=running' --format '{{.CurrentState}}' | head -n1"
$serviceStatus = Invoke-SSHCommand $statusCmd

Write-Host "   Status: $serviceStatus" -ForegroundColor Gray

if ($serviceStatus -match "Running") {
    Write-Host "   ✅ Serviço atualizado e rodando!" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Serviço pode não estar rodando corretamente" -ForegroundColor Yellow
}

Write-Host "`n🧪 ETAPA 4: Testando scraping na VPS..." -ForegroundColor Green
Write-Host "   Fazendo requisição de teste..." -ForegroundColor Gray

# Teste com 2 produtos apenas
$testPayload = '{"max_produtos": 2}'

Write-Host "   Executando: POST /scrape/ofertas (max 2 produtos)..." -ForegroundColor Gray
$testResult = curl.exe -k -X POST https://scraperofertas.soluztions.shop/scrape/ofertas `
    -H "Content-Type: application/json" `
    -H "X-API-Key: egn-2025-secret-key" `
    -d $testPayload `
    --max-time 120

Write-Host "`n📊 RESULTADO DO TESTE:" -ForegroundColor Yellow
Write-Host $testResult -ForegroundColor White

# Parse do resultado
$needsProxy = $false
try {
    $result = $testResult | ConvertFrom-Json
    
    Write-Host "`n" -NoNewline
    Write-Host ("="*70) -ForegroundColor Cyan
    Write-Host "  📈 ANÁLISE DO RESULTADO" -ForegroundColor Yellow
    Write-Host ("="*70) -ForegroundColor Cyan
    
    Write-Host "`nTotal de produtos testados: $($result.total)" -ForegroundColor White
    Write-Host "Produtos COM link de afiliado: " -NoNewline
    
    if ($result.total_com_link -gt 0) {
        Write-Host "$($result.total_com_link) ✅" -ForegroundColor Green
    } else {
        Write-Host "$($result.total_com_link) ❌" -ForegroundColor Red
    }
    
    Write-Host "Produtos SEM link: $($result.total_sem_link)" -ForegroundColor White
    
    # Verifica sucesso
    if ($result.total_com_link -gt 0) {
        Write-Host "`n🎉 SUCESSO! Anti-bot funcionando na VPS!" -ForegroundColor Green
        Write-Host "   As otimizações estão funcionando:" -ForegroundColor Green
        Write-Host "   ✅ Navegação humana ativa" -ForegroundColor Green
        Write-Host "   ✅ Chrome/Chromium com anti-detecção" -ForegroundColor Green
        Write-Host "   ✅ Delays humanizados" -ForegroundColor Green
        
    } else {
        Write-Host "`n⚠️ AINDA COM PROBLEMA - Possível bloqueio persistente" -ForegroundColor Yellow
        Write-Host "`nPróxima ação recomendada: CONFIGURAR PROXY RESIDENCIAL" -ForegroundColor Yellow
        Write-Host ("="*70) -ForegroundColor Yellow
        $needsProxy = $true
    }
    
}
catch {
    Write-Host "`n❌ Erro ao analisar resultado" -ForegroundColor Red
    Write-Host "Resposta bruta: $testResult" -ForegroundColor Gray
}

# Verifica logs recentes
Write-Host "`n📋 ETAPA 5: Verificando logs recentes..." -ForegroundColor Green

$logsCmd = "docker service logs ${SERVICE_NAME} --tail 50 | grep -E '(HUMANA|Compartilhar|✅|❌|account-verification)' | tail -20"
Write-Host "   Buscando linhas relevantes nos logs..." -ForegroundColor Gray

$logs = Invoke-SSHCommand $logsCmd

if ($logs) {
    Write-Host "`n📜 Logs relevantes:" -ForegroundColor Cyan
    Write-Host $logs -ForegroundColor Gray
    
    # Analisa logs para detectar problemas
    if ($logs -match "account-verification") {
        Write-Host "`n⚠️ DETECTADO: Redirect para account-verification" -ForegroundColor Red
        Write-Host "   ML ainda está bloqueando mesmo com otimizações" -ForegroundColor Red
        Write-Host "   SOLUÇÃO: Configure proxy residencial brasileiro" -ForegroundColor Yellow
        
        $needsProxy = $true
    }
    
    if ($logs -match "Navegação humana concluída") {
        Write-Host "`n✅ Navegação humana está ativa" -ForegroundColor Green
    }
    
} else {
    Write-Host "   ⚠️ Logs vazios ou inacessíveis" -ForegroundColor Yellow
}

# Instruções finais
Write-Host "`n" -NoNewline
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host "  📚 PRÓXIMOS PASSOS" -ForegroundColor Yellow
Write-Host ("="*70) -ForegroundColor Cyan

if ($result.total_com_link -gt 0) {
    Write-Host "`n✅ Sistema funcionando! Pode usar em produção." -ForegroundColor Green
    Write-Host "`nComandos úteis:" -ForegroundColor White
    Write-Host "  Ver logs completos:" -ForegroundColor Gray
    Write-Host "    ssh root@${VPS_HOST} 'docker service logs ${SERVICE_NAME} --tail 100'" -ForegroundColor Gray
    Write-Host "`n  Testar novamente:" -ForegroundColor Gray
    Write-Host "    curl -k -X POST https://scraperofertas.soluztions.shop/scrape/ofertas -H 'X-API-Key: egn-2025-secret-key' -d '{\"max_produtos\": 5}'" -ForegroundColor Gray
    
} else {
    Write-Host "`n⚠️ Ainda com bloqueio - CONFIGURE PROXY RESIDENCIAL" -ForegroundColor Yellow
    Write-Host "`nEXECUTE:" -ForegroundColor White
    Write-Host "  .\configure_proxy.ps1" -ForegroundColor Cyan
    Write-Host "`nOu siga instruções em:" -ForegroundColor White
    Write-Host "  ANTI_BOT_CONFIG.md (seção 'Proxy')" -ForegroundColor Cyan
    
    Write-Host "`nProvedores recomendados:" -ForegroundColor White
    Write-Host "  1. Bright Data: https://brightdata.com (melhor)" -ForegroundColor Gray
    Write-Host "  2. Oxylabs: https://oxylabs.io" -ForegroundColor Gray
    Write-Host "  3. Smartproxy: https://smartproxy.com" -ForegroundColor Gray
    Write-Host "`n  IMPORTANTE: Use proxy RESIDENCIAL brasileiro" -ForegroundColor Yellow
}

Write-Host "`n" -NoNewline
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host "  ✨ Deploy concluído!" -ForegroundColor Green
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host ""