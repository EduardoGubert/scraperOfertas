# 🔥 Scraper ML Ofertas - Interface Gráfica

Interface gráfica moderna para o scraper do Mercado Livre com funcionalidades completas.

## ✨ Recursos

- **🔐 Atualizar Login**: Renovação automática do login no ML
- **🚀 Iniciar Scraping**: Execução do pipeline completo
- **📊 Logs em Tempo Real**: Acompanhamento visual do progresso
- **⚙️ Configurável**: Número de produtos personalizável
- **🛡️ Seguro**: Threading para interface responsiva

## 🖥️ Como Usar a Interface

### 1. Executar o GUI
```bash
python gui_scraper.py
```

### 2. Configurações
- **Número de produtos**: Digite quantos produtos deseja processar (padrão: 20)

### 3. Operações
1. **Atualizar Login**: Clique para abrir navegador e fazer login manual
2. **Iniciar Scraping**: Começa o processo de scraping após confirmação

### 4. Monitoramento
- **Status**: Mostra o estado atual da operação
- **Log**: Exibe progresso em tempo real
- **Botões**: Desabilitados durante operações para evitar conflitos

## 📦 Gerar Executável

### Método 1: Script Automático (Recomendado)
```powershell
.\criar_executavel.ps1
```

### Método 2: Manual
```bash
# Instalar PyInstaller
pip install pyinstaller

# Gerar executável
pyinstaller --onefile --windowed --name="ScraperML-egnOfertas" gui_scraper.py
```

O executável será criado em: `dist/ScraperML-egnOfertas.exe`

## 📋 Pré-requisitos

1. **Python 3.8+** instalado
2. **Dependências instaladas**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. **Arquivo .env** configurado com credenciais do banco
4. **Estar na pasta correta** do projeto

## 🎯 Funcionalidades

### Login Automático
- Abre navegador para login manual no ML
- Salva cookies automaticamente
- Detecta login válido

### Scraping Inteligente
- Acessa ofertas relâmpago automaticamente
- Extração de dados completa (nome, foto, preços, desconto)
- Geração de links de afiliado
- Salva no banco PostgreSQL

### Interface Responsiva
- Logs coloridos por tipo de mensagem
- Barra de status dinâmica
- Threading para não travar a interface
- Validações de entrada

## 🔧 Solução de Problemas

### "Erro de Importação"
- Verifique se está executando na pasta correta
- Confirme que todos os arquivos estão presentes

### "Execute o programa na pasta correta"
- Navegue até a pasta que contém:
  - `scraper_ml_afiliado.py`
  - `pipeline.py`
  - `database.py`

### "Falha ao fazer login"
- Verifique conexão com internet
- Tente o login manual no navegador
- Execute novamente o processo

### GUI não abre
- Verifique se tkinter está instalado
- No Linux: `sudo apt-get install python3-tk`
- No Windows/Mac: Vem com Python

## 📝 Arquivos Principais

- `gui_scraper.py` - Interface gráfica principal
- `criar_executavel.ps1` - Script para gerar .exe
- `scraper_ml_afiliado.py` - Motor de scraping
- `pipeline.py` - Orquestrador do processo
- `database.py` - Gerenciador do banco

## 👤 Desenvolvido por

**Eduardo - egnOfertas**

Interface gráfica profissional para automação de scraping do Mercado Livre com integração completa ao pipeline de dados.