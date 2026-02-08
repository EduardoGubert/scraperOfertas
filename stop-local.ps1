# ========================================
# STOP LOCAL - egnOfertas
# Para todos os serviços locais
# ========================================

Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  🛑 PARANDO AMBIENTE LOCAL - egnOfertas" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

Write-Host "`n⏳ Parando containers..." -ForegroundColor Yellow

docker compose -f docker-compose.local.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Todos os serviços foram parados!" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 Os dados foram preservados nos volumes Docker." -ForegroundColor Cyan
    Write-Host "   Para reiniciar: .\start-local.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🗑️  Para remover TUDO (inclusive dados):" -ForegroundColor Yellow
    Write-Host "   docker compose -f docker-compose.local.yml down -v" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "`n❌ Erro ao parar serviços!" -ForegroundColor Red
    exit 1
}