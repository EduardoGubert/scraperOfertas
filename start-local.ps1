# ========================================
# START LOCAL - egnOfertas
# Inicia ambiente local completo
# ========================================

Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  🚀 INICIANDO AMBIENTE LOCAL - egnOfertas" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

# ----------------------------------------
# 1. Verificações
# ----------------------------------------
Write-Host "`n📋 Verificando pré-requisitos..." -ForegroundColor Yellow

# Verifica Docker
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerInstalled) {
    Write-Host "❌ Docker não encontrado! Instale: https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker encontrado: $(docker --version)" -ForegroundColor Green

# Verifica Docker Compose
$composeInstalled = docker compose version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker Compose não encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker Compose encontrado" -ForegroundColor Green

# ----------------------------------------
# 2. Cria pasta de debug
# ----------------------------------------
if (-not (Test-Path "debug_screenshots")) {
    New-Item -ItemType Directory -Path "debug_screenshots" | Out-Null
    Write-Host "✅ Pasta debug_screenshots criada" -ForegroundColor Green
}

# ----------------------------------------
# 3. Para containers antigos (se existirem)
# ----------------------------------------
Write-Host "`n🛑 Parando containers antigos (se existirem)..." -ForegroundColor Yellow

docker compose -f docker-compose.local.yml down 2>$null

# ----------------------------------------
# 4. Build da imagem do scraper
# ----------------------------------------
Write-Host "`n🔨 Buildando imagem do scraper..." -ForegroundColor Yellow
Write-Host "   ⏳ Isso pode demorar 2-5 minutos (instalando Chrome + Chromium)..." -ForegroundColor Gray

docker compose -f docker-compose.local.yml build --no-cache scraper-ml-afiliado

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Falha no build da imagem!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Imagem buildada com sucesso!" -ForegroundColor Green

# ----------------------------------------
# 5. Inicia todos os serviços
# ----------------------------------------
Write-Host "`n🚀 Iniciando todos os serviços..." -ForegroundColor Yellow

docker compose -f docker-compose.local.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Falha ao iniciar serviços!" -ForegroundColor Red
    exit 1
}

# ----------------------------------------
# 6. Aguarda serviços ficarem prontos
# ----------------------------------------
Write-Host "`n⏳ Aguardando serviços iniciarem..." -ForegroundColor Yellow

Write-Host "   🗄️  PostgreSQL..." -NoNewline
$maxRetries = 30
$retry = 0
while ($retry -lt $maxRetries) {
    $pgReady = docker exec egn_postgres_local pg_isready -U egn_user -d egn_ofertas 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 2
    $retry++
}

if ($retry -ge $maxRetries) {
    Write-Host " ❌ Timeout" -ForegroundColor Red
}

Write-Host "   📊 n8n..." -NoNewline
$retry = 0
while ($retry -lt $maxRetries) {
    try {
        $n8nReady = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($n8nReady.StatusCode -eq 200) {
            Write-Host " ✅" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Seconds 2
    $retry++
}

if ($retry -ge $maxRetries) {
    Write-Host " ❌ Timeout" -ForegroundColor Red
}

Write-Host "   🕷️  Scraper ML..." -NoNewline
$retry = 0
while ($retry -lt $maxRetries) {
    try {
        $scraperReady = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($scraperReady.StatusCode -eq 200) {
            Write-Host " ✅" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Seconds 2
    $retry++
}

if ($retry -ge $maxRetries) {
    Write-Host " ❌ Timeout (mas container pode estar OK)" -ForegroundColor Yellow
}

# ----------------------------------------
# 7. Informações de acesso
# ----------------------------------------
Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "  ✅ AMBIENTE LOCAL INICIADO COM SUCESSO!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

Write-Host "`n📊 SERVIÇOS DISPONÍVEIS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🗄️  PostgreSQL:" -ForegroundColor Yellow
Write-Host "     Host: localhost:5432"
Write-Host "     Database: egn_ofertas"
Write-Host "     User: egn_user"
Write-Host "     Password: egn_password_2025"
Write-Host ""
Write-Host "  📊 n8n (Workflow Automation):" -ForegroundColor Yellow
Write-Host "     URL: http://localhost:5678"
Write-Host "     User: admin"
Write-Host "     Password: egn2025admin"
Write-Host ""
Write-Host "  🕷️  Scraper ML Afiliado:" -ForegroundColor Yellow
Write-Host "     API: http://localhost:8000"
Write-Host "     Docs: http://localhost:8000/docs"
Write-Host "     Health: http://localhost:8000/health"
Write-Host "     API Key: egn-2025-secret-key"
Write-Host ""

Write-Host "🔧 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1️⃣  Fazer login no ML (local):" -ForegroundColor White
Write-Host "     python login_local.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  2️⃣  Abrir n8n e importar workflow:" -ForegroundColor White
Write-Host "     http://localhost:5678" -ForegroundColor Gray
Write-Host "     Import: egnOfertas - ML Promoções WhatsApp v2 (Scraper Direto).json" -ForegroundColor Gray
Write-Host ""
Write-Host "  3️⃣  Configurar no workflow n8n:" -ForegroundColor White
Write-Host "     • scraper_url: http://scraper-ml-afiliado:8000" -ForegroundColor Gray
Write-Host "     • scraper_api_key: egn-2025-secret-key" -ForegroundColor Gray
Write-Host "     • evolution_url: https://evolution.soluztions.shop (servidor remoto)" -ForegroundColor Gray
Write-Host "     • evolution_api_key: 7177bcb5d4b424d60f82dfd42f3ef758" -ForegroundColor Gray
Write-Host "     • whatsapp_group_jid: (seu JID do grupo)" -ForegroundColor Gray
Write-Host ""

Write-Host "📝 COMANDOS ÚTEIS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Ver logs:          docker compose -f docker-compose.local.yml logs -f" -ForegroundColor Gray
Write-Host "  Parar tud o:        docker compose -f docker-compose.local.yml down" -ForegroundColor Gray
Write-Host "  Reiniciar:         docker compose -f docker-compose.local.yml restart" -ForegroundColor Gray
Write-Host "  Status:            docker compose -f docker-compose.local.yml ps" -ForegroundColor Gray
Write-Host ""

Write-Host "=" * 70 -ForegroundColor Green
Write-Host ""