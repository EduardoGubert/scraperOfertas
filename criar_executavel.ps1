# Script para criar executável do Scraper ML
# Execute este arquivo para gerar o .exe

Write-Host "🔧 Criando executável do Scraper ML Ofertas..." -ForegroundColor Green

# Verifica se PyInstaller está instalado
try {
    pyinstaller --version | Out-Null
    Write-Host "✅ PyInstaller encontrado" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Instalando PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Remove builds anteriores
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "*.spec") { Remove-Item -Force "*.spec" }

Write-Host "🚀 Gerando executável..." -ForegroundColor Green

# Gera o executável
pyinstaller --onefile --windowed --name="ScraperML-egnOfertas" --icon=icon.ico gui_scraper.py

# Verifica se foi criado com sucesso
if (Test-Path "dist\ScraperML-egnOfertas.exe") {
    Write-Host "✅ Executável criado com sucesso!" -ForegroundColor Green
    Write-Host "📍 Localização: dist\ScraperML-egnOfertas.exe" -ForegroundColor Cyan
    
    # Cria pasta de distribuição
    if (-not(Test-Path "distribuicao")) { New-Item -ItemType Directory -Name "distribuicao" }
    
    # Copia executável e arquivos necessários
    Copy-Item "dist\ScraperML-egnOfertas.exe" "distribuicao\"
    Copy-Item ".env.example" "distribuicao\" -ErrorAction SilentlyContinue
    
    Write-Host "📦 Arquivos organizados na pasta 'distribuicao'" -ForegroundColor Green
    
    # Pergunta se quer abrir a pasta
    $response = Read-Host "Abrir pasta de distribuição? (s/n)"
    if ($response -eq "s" -or $response -eq "S") {
        explorer "distribuicao"
    }
    
} else {
    Write-Host "❌ Erro ao criar executável" -ForegroundColor Red
    Write-Host "Verifique os logs acima para detalhes" -ForegroundColor Yellow
}

Write-Host "🏁 Processo concluído!" -ForegroundColor Green