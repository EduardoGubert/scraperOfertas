# Stop local environment
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$ComposeFile = "deploy/docker/docker-compose.local.yml"

docker compose -f $ComposeFile down
if ($LASTEXITCODE -eq 0) {
    Write-Host "Local environment stopped." -ForegroundColor Green
} else {
    Write-Host "Failed to stop environment." -ForegroundColor Red
    exit 1
}
