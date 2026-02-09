#!/usr/bin/env pwsh
# Sync local cookies to running local container

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$LocalCookies = "./ml_browser_data"
$ContainerName = "egn_scraper_local"

if (-not (Test-Path $LocalCookies)) {
    Write-Host "Cookies folder not found. Run: python -m apps.scraper.login_local" -ForegroundColor Red
    exit 1
}

$containerRunning = docker ps --filter "name=$ContainerName" --format "{{.Names}}" 2>$null
if (-not $containerRunning) {
    Write-Host "Container not running. Start with scripts/windows/start-local.ps1" -ForegroundColor Yellow
    exit 0
}

docker exec $ContainerName sh -c "rm -f /app/ml_browser_data/SingletonLock /app/ml_browser_data/SingletonSocket /app/ml_browser_data/SingletonCookie" 2>$null
docker restart $ContainerName | Out-Null
Write-Host "Cookies synced (container restarted)." -ForegroundColor Green
