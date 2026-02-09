# Start local environment
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$ComposeFile = "deploy/docker/docker-compose.local.yml"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "STARTING LOCAL ENVIRONMENT" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found." -ForegroundColor Red
    exit 1
}

docker compose -f $ComposeFile down 2>$null

docker compose -f $ComposeFile build --no-cache scraper-ml-afiliado
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

docker compose -f $ComposeFile up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Startup failed." -ForegroundColor Red
    exit 1
}

Write-Host "`nServices are up." -ForegroundColor Green
Write-Host "API:  http://localhost:8000" -ForegroundColor Gray
Write-Host "N8N:  http://localhost:5678" -ForegroundColor Gray
Write-Host "DB:   localhost:5432" -ForegroundColor Gray
Write-Host "`nNext login step:" -ForegroundColor Cyan
Write-Host "python -m apps.scraper.login_local" -ForegroundColor Gray
