# Build GUI executable
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    pip install pyinstaller
}

if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "*.spec") { Remove-Item -Force "*.spec" }

pyinstaller --onefile --windowed --name="ScraperML-egnOfertas" apps/gui/main.py

if (Test-Path "dist\ScraperML-egnOfertas.exe") {
    if (-not (Test-Path "distribuicao")) { New-Item -ItemType Directory -Path "distribuicao" | Out-Null }
    Copy-Item "dist\ScraperML-egnOfertas.exe" "distribuicao\" -Force
    if (Test-Path "config\env\.env.example") {
        Copy-Item "config\env\.env.example" "distribuicao\" -Force
    }
    Write-Host "Executable generated: dist\ScraperML-egnOfertas.exe" -ForegroundColor Green
} else {
    Write-Host "Failed to generate executable." -ForegroundColor Red
    exit 1
}
