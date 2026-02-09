# GUI scraperOfertas

Interface Tkinter para executar jobs individualmente ou em sequencia sem travar a UI.

## Executar GUI

```bash
python -m apps.gui.main
```

## Botoes disponiveis

- `Atualizar Login`
- `Scraper Ofertas`
- `Scraper Ofertas Relampago`
- `Scraper Cupons`
- `Executar Todos`

## Gerar executavel (Windows)

### Script pronto

```powershell
./scripts/windows/criar_executavel.ps1
```

### Manual (opcional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name="ScraperML-egnOfertas" apps/gui/main.py
```

Saida esperada: `dist/ScraperML-egnOfertas.exe`

## Pre-requisitos

```bash
pip install -r config/python/requirements.txt
playwright install chromium
```

Arquivo de ambiente: `config/env/.env`.

## Arquivos principais

- `apps/gui/main.py`
- `src/presentation/gui/app.py`
- `apps/scraper/login_local.py`
- `scripts/windows/criar_executavel.ps1`
