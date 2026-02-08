# ============================================
# REBUILD E DEPLOY DA IMAGEM DOCKER
# ============================================
#
# Este script faz o build da nova image e faz deploy na VPS
#
# ============================================

$IMAGE_NAME = "eduardopoa/scraper-ml-afiliado"
$VERSION = "latest"
$VPS_HOST = "72.60.51.81"
$VPS_USER = "root"
$STACK_NAME = "scraperofertas"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BUILD E DEPLOY - SCRAPER ML AFILIADO" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Build da imagem
Write-Host "[1/5] Building Docker image..." -ForegroundColor Yellow
docker build -t ${IMAGE_NAME}:${VERSION} .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha no build!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Build concluído!" -ForegroundColor Green

# 2. Push para Docker Hub
Write-Host ""
Write-Host "[2/5] Pushing para Docker Hub..." -ForegroundColor Yellow
docker push ${IMAGE_NAME}:${VERSION}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha no push!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Push concluído!" -ForegroundColor Green

# 3. Pull na VPS
Write-Host ""
Write-Host "[3/5] Fazendo pull na VPS..." -ForegroundColor Yellow
ssh ${VPS_USER}@${VPS_HOST} "docker pull ${IMAGE_NAME}:${VERSION}"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha no pull!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Pull concluído!" -ForegroundColor Green

# 4. Atualizar serviço
Write-Host ""
Write-Host "[4/5] Atualizando serviço Docker Swarm..." -ForegroundColor Yellow
ssh ${VPS_USER}@${VPS_HOST} "docker service update --image ${IMAGE_NAME}:${VERSION} --force ${STACK_NAME}_scraper-ml-afiliado"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao atualizar serviço!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Serviço atualizado!" -ForegroundColor Green

# 5. Verificar status
Write-Host ""
Write-Host "[5/5] Aguardando serviço estabilizar..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DEPLOY CONCLUÍDO!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verifique os logs:" -ForegroundColor Yellow
Write-Host "  ssh ${VPS_USER}@${VPS_HOST} 'docker service logs ${STACK_NAME}_scraper-ml-afiliado --tail 50'" -ForegroundColor White
Write-Host ""
Write-Host "Verifique o status:" -ForegroundColor Yellow
Write-Host "  curl.exe -k https://scraperofertas.soluztions.shop/auth/status -H 'X-API-Key: egn-2025-secret-key'" -ForegroundColor White
Write-Host ""
Write-Host "Screenshots de debug estarão em:" -ForegroundColor Yellow
Write-Host "  ssh ${VPS_USER}@${VPS_HOST} 'docker exec -it \$(docker ps -qf name=${STACK_NAME}_scraper-ml-afiliado) ls -lh /app/debug_*.png'" -ForegroundColor White
Write-Host ""
