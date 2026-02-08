#!/usr/bin/env pwsh
# Extrai screenshots e debug do container

Write-Host "`nEXTRAINDO DEBUG DO CONTAINER" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Gray

$CONTAINER = "egn_scraper_local"
$LOCAL_DEBUG = ".\debug_container"

# Cria pasta local
if (-not (Test-Path $LOCAL_DEBUG)) {
    New-Item -ItemType Directory -Path $LOCAL_DEBUG | Out-Null
}

Write-Host "`nCopiando screenshots do container..." -ForegroundColor Yellow

# Lista arquivos no container
$files = docker exec $CONTAINER sh -c "ls -1 /app/debug_produto_*.png 2>/dev/null" 2>$null

if ($LASTEXITCODE -ne 0 -or -not $files) {
    Write-Host "   Nenhum screenshot encontrado no container" -ForegroundColor Yellow
    Write-Host "   Tentando pasta debug_screenshots..." -ForegroundColor Gray
    
    $files = docker exec $CONTAINER sh -c "ls -1 /app/debug_screenshots/debug_produto_*.png 2>/dev/null" 2>$null
    
    if ($LASTEXITCODE -ne 0 -or -not $files) {
        Write-Host "   Nenhum screenshot em debug_screenshots tambem" -ForegroundColor Red
        Write-Host "`nExecute um scraping primeiro:" -ForegroundColor Cyan
        Write-Host '   curl -X POST http://localhost:8000/scrape/ofertas -H "X-API-Key: egn-2025-secret-key" -H "Content-Type: application/json" -d "{\"max_produtos\": 2}"' -ForegroundColor Gray
        exit 1
    }
}

# Copia cada arquivo
$fileList = $files -split "`n"
$copied = 0

foreach ($file in $fileList) {
    $file = $file.Trim()
    if ($file) {
        $filename = Split-Path -Leaf $file
        Write-Host "   $filename" -ForegroundColor White
        docker cp "${CONTAINER}:$file" "$LOCAL_DEBUG\$filename" 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            $copied++
        }
    }
}

# Copia HTMLs tambem
Write-Host "`nCopiando HTMLs do container..." -ForegroundColor Yellow

$htmlFiles = docker exec $CONTAINER sh -c "ls -1 /app/debug_produto_*.html 2>/dev/null" 2>$null

if ($htmlFiles) {
    $htmlList = $htmlFiles -split "`n"
    foreach ($file in $htmlList) {
        $file = $file.Trim()
        if ($file) {
            $filename = Split-Path -Leaf $file
            Write-Host "   $filename" -ForegroundColor White
            docker cp "${CONTAINER}:$file" "$LOCAL_DEBUG\$filename" 2>&1 | Out-Null
        }
    }
}

Write-Host "`nCopiados $copied arquivos para $LOCAL_DEBUG" -ForegroundColor Green

# Abre pasta no Explorer
Write-Host "`nAbrindo pasta no Explorer..." -ForegroundColor Yellow
Start-Process explorer.exe -ArgumentList (Resolve-Path $LOCAL_DEBUG)

# Estatisticas dos screenshots
Write-Host "`nUltimos 3 screenshots:" -ForegroundColor Cyan
Get-ChildItem -Path $LOCAL_DEBUG -Filter "*.png" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 3 |
    ForEach-Object {
        $size = [math]::Round($_.Length / 1KB, 2)
        Write-Host "   $($_.Name) ($size KB) - $($_.LastWriteTime)" -ForegroundColor White
    }

Write-Host "`nPROXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Veja os screenshots para entender o estado da pagina" -ForegroundColor White
Write-Host "2. Procure pelo modal de compartilhar" -ForegroundColor White
Write-Host "3. Se modal nao aparece, pode ser:" -ForegroundColor White
Write-Host "   - Delay insuficiente apos clique" -ForegroundColor Gray
Write-Host "   - Botao errado sendo clicado" -ForegroundColor Gray
Write-Host "   - Modal com seletor diferente" -ForegroundColor Gray
Write-Host "   - Necessario estar logado como afiliado" -ForegroundColor Gray
Write-Host ""

