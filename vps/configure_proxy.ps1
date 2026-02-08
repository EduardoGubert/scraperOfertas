#!/usr/bin/env pwsh
# Configuração de Proxy na VPS
# Uso: .\configure_proxy.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n" -NoNewline
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host "  🌐 CONFIGURAÇÃO DE PROXY - VPS" -ForegroundColor Yellow
Write-Host ("="*70) -ForegroundColor Cyan

Write-Host "`nEste script configura proxy residencial na VPS para evitar bloqueio do ML" -ForegroundColor White

# Coleta informações do proxy
Write-Host "`n📋 INFORMAÇÕES DO PROXY:" -ForegroundColor Green
Write-Host "   (deixe em branco se não tiver username/password)" -ForegroundColor Gray

$proxyServer = Read-Host "`n🌐 URL do proxy (ex: http://proxy.com:8080)"

if (-not $proxyServer) {
    Write-Host "`n❌ URL do proxy é obrigatória!" -ForegroundColor Red
    exit 1
}

$proxyUser = Read-Host "👤 Username (Enter para pular)"
$proxyPass = Read-Host "🔑 Password (Enter para pular)" -AsSecureString

# Converte SecureString para texto plano
$proxyPassPlain = ""
if ($proxyPass.Length -gt 0) {
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($proxyPass)
    $proxyPassPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# Configurações VPS
$VPS_HOST = "72.60.51.81"
$VPS_USER = "root"
$VPS_PASS = "B@ruck151022#@"
$SERVICE_NAME = "scraperofertas_scraper-ml-afiliado"
$STACK_NAME = "scraperofertas"

Write-Host "`n📝 Resumo da configuração:" -ForegroundColor Yellow
Write-Host "   Servidor: $proxyServer" -ForegroundColor White
Write-Host "   Username: $(if ($proxyUser) { $proxyUser } else { '(não configurado)' })" -ForegroundColor White
Write-Host "   Password: $(if ($proxyPassPlain) { '***' } else { '(não configurado)' })" -ForegroundColor White

$confirm = Read-Host "`n❓ Confirma configuração? (S/n)"
if ($confirm -eq "n" -or $confirm -eq "N") {
    Write-Host "❌ Cancelado pelo usuário" -ForegroundColor Red
    exit 0
}

Write-Host "`n🔧 Conectando na VPS..." -ForegroundColor Green

# Cria/atualiza arquivo .env na VPS
$envContent = @"
PROXY_SERVER=$proxyServer
$(if ($proxyUser) { "PROXY_USER=$proxyUser" } else { "" })
$(if ($proxyPassPlain) { "PROXY_PASS=$proxyPassPlain" } else { "" })
"@

Write-Host "   Criando arquivo .env..." -ForegroundColor Gray

# Envia .env via SSH
$tmpFile = [System.IO.Path]::GetTempFileName()
$envContent | Out-File -FilePath $tmpFile -Encoding utf8 -NoNewline

# Upload via SCP
Write-Host "   Enviando configurações..." -ForegroundColor Gray
scp $tmpFile "root@${VPS_HOST}:/root/scraperofertas/.env"

Remove-Item $tmpFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro ao enviar .env!" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Arquivo .env criado na VPS" -ForegroundColor Green

# Atualiza docker-compose.yml para usar .env
Write-Host "`n📝 Atualizando docker-compose.yml..." -ForegroundColor Green

$composeUpdate = @"
ssh root@${VPS_HOST} 'cd /root/scraperofertas && cat > docker-compose.scraperofertas.yml << EOF
version: \"3.8\"

services:
  scraper-ml-afiliado:
    image: eduardogubert/scraperofertas:latest
    environment:
      - DISPLAY=:99
      - PROXY_SERVER=\${PROXY_SERVER}
      - PROXY_USER=\${PROXY_USER}
      - PROXY_PASS=\${PROXY_PASS}
    volumes:
      - ./ml_browser_data:/app/ml_browser_data
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    ports:
      - \"8000:8000\"
    networks:
      - ml-network

networks:
  ml-network:
    driver: overlay
EOF'
"@

Invoke-Expression $composeUpdate

Write-Host "   ✅ docker-compose.yml atualizado" -ForegroundColor Green

# Atualiza api_ml_afiliado.py para ler proxy do ambiente
Write-Host "`n🔧 Verificando api_ml_afiliado.py..." -ForegroundColor Green
Write-Host "   (certifique-se que o código lê as variáveis de ambiente)" -ForegroundColor Gray

# Redeployou stack
Write-Host "`n🔄 Reaplicando stack com proxy..." -ForegroundColor Green

$redeployCmd = @"
cd /root/scraperofertas && \
docker stack deploy -c docker-compose.scraperofertas.yml --with-registry-auth $STACK_NAME
"@

ssh "root@${VPS_HOST}" $redeployCmd

Write-Host "   ⏳ Aguardando serviço reiniciar..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# Verifica status
$statusCmd = "docker service ps ${SERVICE_NAME} --filter 'desired-state=running' --format '{{.CurrentState}}'"
$serviceStatus = ssh "root@${VPS_HOST}" $statusCmd

Write-Host "   Status: $serviceStatus" -ForegroundColor Gray

if ($serviceStatus -match "Running") {
    Write-Host "   ✅ Serviço rodando com proxy!" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Serviço pode não estar rodando" -ForegroundColor Yellow
}

# Testa proxy
Write-Host "`n🧪 Testando proxy..." -ForegroundColor Green

$testCmd = @"
CONTAINER_ID=\$(docker ps -qf name=${SERVICE_NAME})
docker exec \$CONTAINER_ID python -c \"
import os
proxy = os.getenv('PROXY_SERVER')
user = os.getenv('PROXY_USER')
print(f'Proxy configurado: {proxy}')
print(f'Username: {user if user else \"(sem autenticacao)\"}')
\"
"@

$proxyTest = ssh "root@${VPS_HOST}" $testCmd

Write-Host "   Resultado:" -ForegroundColor Gray
Write-Host $proxyTest -ForegroundColor White

# Teste de scraping
Write-Host "`n🔍 Testando scraping com proxy..." -ForegroundColor Green

$testPayload = '{"max_produtos": 2}'
$testResult = curl.exe -k -X POST https://scraperofertas.soluztions.shop/scrape/ofertas `
    -H "Content-Type: application/json" `
    -H "X-API-Key: egn-2025-secret-key" `
    -d $testPayload `
    --max-time 120

Write-Host "`n📊 RESULTADO:" -ForegroundColor Yellow
Write-Host $testResult -ForegroundColor White

try {
    $result = $testResult | ConvertFrom-Json
    
    Write-Host "`n" -NoNewline
    Write-Host ("="*70) -ForegroundColor Cyan
    
    if ($result.total_com_link -gt 0) {
        Write-Host "  🎉 SUCESSO! Proxy funcionando!" -ForegroundColor Green
        Write-Host ("="*70) -ForegroundColor Cyan
        Write-Host "`nProdutos com link: $($result.total_com_link) ✅" -ForegroundColor Green
        Write-Host "Produtos sem link: $($result.total_sem_link)" -ForegroundColor White
        
    } else {
        Write-Host "  ⚠️ Ainda sem sucesso" -ForegroundColor Yellow
        Write-Host ("="*70) -ForegroundColor Cyan
        Write-Host "`nPossíveis problemas:" -ForegroundColor Yellow
        Write-Host "  1. Proxy não está funcionando (teste manualmente)" -ForegroundColor Gray
        Write-Host "  2. Proxy não é residencial (usa datacenter)" -ForegroundColor Gray
        Write-Host "  3. IP do proxy já está bloqueado pelo ML" -ForegroundColor Gray
        Write-Host "`nRecomendação:" -ForegroundColor Yellow
        Write-Host "  - Teste o proxy manualmente:" -ForegroundColor White
        Write-Host "    curl --proxy $proxyServer https://api.ipify.org" -ForegroundColor Gray
        Write-Host "  - Verifique se é proxy RESIDENCIAL brasileiro" -ForegroundColor White
        Write-Host "  - Tente outro provedor (Bright Data, Oxylabs)" -ForegroundColor White
    }
    
} catch {
    Write-Host "❌ Erro ao analisar resposta" -ForegroundColor Red
}

Write-Host "`n" -NoNewline
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host "  ✨ Configuração concluída!" -ForegroundColor Green
Write-Host ("="*70) -ForegroundColor Cyan

Write-Host "`n📚 Comandos úteis:" -ForegroundColor White
Write-Host "  Ver variáveis de ambiente:" -ForegroundColor Gray
Write-Host "    ssh root@${VPS_HOST} 'cat /root/scraperofertas/.env'" -ForegroundColor Gray
Write-Host "`n  Ver logs:" -ForegroundColor Gray
Write-Host "    ssh root@${VPS_HOST} 'docker service logs ${SERVICE_NAME} --tail 50'" -ForegroundColor Gray
Write-Host "`n  Testar novamente:" -ForegroundColor Gray
Write-Host "    curl -k -X POST https://scraperofertas.soluztions.shop/scrape/ofertas -H 'X-API-Key: egn-2025-secret-key' -d '{\"max_produtos\": 2}'" -ForegroundColor Gray
Write-Host ""
