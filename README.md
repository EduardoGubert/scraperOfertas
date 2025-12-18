# 🛒 Scraper ML Afiliado

Scraper automatizado para extrair ofertas do Mercado Livre **com links de afiliado válidos**.

## ✨ O que faz

1. **Loga** na sua conta de afiliado ML (uma vez)
2. **Acessa** a página de ofertas
3. **Para cada produto**: clica → compartilha → extrai o link curto de afiliado
4. **Retorna** dados completos com:
   - Nome, preço, desconto
   - Foto
   - **Link curto de afiliado** (ex: `https://mercadolivre.com/sec/2po39Mc`)
   - MLB ID

## 🎯 Diferencial

Diferente de outros scrapers que só montam links de afiliado "por fora", este:
- ✅ Usa o **sistema oficial** de compartilhamento do ML
- ✅ Adiciona produtos à sua **lista de afiliado** automaticamente
- ✅ Gera links **curtos oficiais** que aparecem no seu perfil
- ✅ O botão "Ir para produto" funciona!

## 🚀 Quick Start

### Instalação

```bash
# Clone ou baixe os arquivos
git clone <seu-repo>
cd scraper-ml-afiliado

# Setup
pip install -r requirements.txt
playwright install chromium
```

### ⚠️ IMPORTANTE: Fluxo para VPS

Como a VPS não tem tela, você precisa fazer o login na sua máquina local primeiro:

```
┌─────────────────────────────────────────────────────────────┐
│  SUA MÁQUINA LOCAL (com tela)                               │
│                                                             │
│  1. python login_vps.py                                     │
│     └─ Navegador abre                                       │
│     └─ Você faz login no ML                                 │
│     └─ Cookies salvos em ml_browser_data/                   │
│     └─ Gera arquivo: ml_cookies_export.tar.gz               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    scp ml_cookies_export.tar.gz usuario@vps:/app/
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  SUA VPS (sem tela)                                         │
│                                                             │
│  2. tar -xzf ml_cookies_export.tar.gz                       │
│  3. python login_vps.py --verificar                         │
│  4. uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000  │
└─────────────────────────────────────────────────────────────┘
```

### Passo a Passo Detalhado

#### 1️⃣ Na sua máquina LOCAL (com tela)

```bash
# Instala dependências
pip install -r requirements.txt
playwright install chromium

# Faz login e exporta cookies
python login_vps.py
```

- O navegador vai abrir
- Faça login com sua conta de afiliado
- Pressione ENTER quando terminar
- Arquivo `ml_cookies_export.tar.gz` será criado

#### 2️⃣ Copie para a VPS

```bash
scp ml_cookies_export.tar.gz usuario@sua-vps:/caminho/do/scraper/
```

#### 3️⃣ Na VPS

```bash
# Extrai os cookies
tar -xzf ml_cookies_export.tar.gz

# Verifica se funcionou
python login_vps.py --verificar

# Roda a API
uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000
```

### ⏰ Renovação de Cookies

Os cookies expiram após alguns dias. Quando parar de funcionar:

1. Rode `python login_vps.py` na sua máquina local novamente
2. Copie o novo arquivo para a VPS
3. Extraia e reinicie o serviço

## 📡 API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Info da API |
| GET | `/health` | Health check + status do login |
| GET | `/login/status` | Verifica se está logado |
| POST | `/login/init` | Inicia browser para login manual |
| POST | `/scrape/ofertas` | **Scraping completo** |
| POST | `/webhook/scrape` | Versão simplificada para n8n |

### Request `/scrape/ofertas`

```json
{
  "url": "https://www.mercadolivre.com.br/ofertas",
  "max_produtos": 50,
  "headless": true
}
```

### Response

```json
{
  "success": true,
  "total": 50,
  "total_com_link": 48,
  "total_sem_link": 2,
  "produtos": [
    {
      "nome": "Tênis Asics Gel Sparta 2 Masculino",
      "preco_atual": 264.90,
      "preco_original": 479.90,
      "desconto": 44,
      "foto_url": "https://http2.mlstatic.com/...",
      "url_curta": "https://mercadolivre.com/sec/2po39Mc",
      "url_afiliado": "https://mercadolivre.com/sec/2po39Mc",
      "mlb_id": "MLB5691495974",
      "status": "sucesso"
    }
  ],
  "scraped_at": "2024-12-18T14:30:00"
}
```

## 🔧 Integração com n8n

### Workflow Exemplo

```
Schedule Trigger (1h)
    ↓
HTTP Request → POST http://scraper:8000/webhook/scrape
    ↓
Filter → desconto > 30
    ↓
Set → Formata mensagem WhatsApp
    ↓
Evolution API → Envia para grupo
```

### Node HTTP Request

- **URL**: `http://scraper-ml-afiliado:8000/webhook/scrape`
- **Method**: POST
- **Headers**: `X-API-Key: sua-chave`
- **Body**: `{"max_produtos": 50}`

## 🐳 Docker

### Build e Run

```bash
# Build
docker build -t scraper-ml-afiliado .

# Run (primeira vez - para login)
docker run -it --rm \
  -p 8000:8000 \
  -v ml_browser_data:/app/ml_browser_data \
  -e DISPLAY=:0 \
  scraper-ml-afiliado python login_manual.py

# Run API
docker run -d \
  -p 8000:8000 \
  -v ml_browser_data:/app/ml_browser_data \
  -e SCRAPER_API_KEY=sua-chave \
  scraper-ml-afiliado
```

### Docker Swarm + Traefik

```bash
docker stack deploy -c docker-compose.yml scraper-ml
```

## 📁 Estrutura

```
scraper-ml-afiliado/
├── scraper_ml_afiliado.py   # Classe principal do scraper
├── api_ml_afiliado.py       # API FastAPI
├── login_manual.py          # Script de login
├── requirements.txt         # Dependências
├── Dockerfile              
├── docker-compose.yml       # Deploy Swarm + Traefik
├── setup.sh                 # Script de setup
├── ml_browser_data/         # Cookies/sessão (gerado)
└── README.md
```

## ⚠️ Limitações e Cuidados

1. **Rate Limiting**: O scraper usa delays humanizados, mas não abuse
   - Recomendado: máx 50-100 produtos por execução
   - Intervalo entre execuções: mínimo 1 hora

2. **Login**: Os cookies expiram eventualmente
   - Se parar de funcionar, rode `login_manual.py` novamente

3. **Detecção**: O ML pode detectar automação
   - Use `headless=True` em produção
   - Não rode múltiplas instâncias

4. **Termos de Uso**: Use por sua conta e risco

## 🔄 Fluxo do Scraper

```
┌─────────────────────────────────────────────────────────────┐
│  1. VERIFICA LOGIN                                          │
│     └─ Cookies salvos? → Tenta usar                         │
│     └─ Não logado? → Pede login manual                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2. ACESSA PÁGINA DE OFERTAS                                │
│     └─ Scroll para carregar lazy loading                    │
│     └─ Extrai lista de URLs dos produtos                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  3. PARA CADA PRODUTO (loop)                                │
│     ├─ Acessa página do produto                             │
│     ├─ Extrai: nome, preço, desconto, foto                  │
│     ├─ Clica em "Compartilhar" (barra afiliados)            │
│     ├─ Aguarda modal abrir                                  │
│     ├─ Extrai link curto (mercadolivre.com/sec/XXX)         │
│     ├─ Fecha modal                                          │
│     └─ Delay humanizado → próximo produto                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  4. RETORNA RESULTADOS                                      │
│     └─ JSON com todos os produtos + links de afiliado       │
└─────────────────────────────────────────────────────────────┘
```

## 📝 Changelog

### v2.0.0
- Novo: Extração de links de afiliado via botão Compartilhar
- Novo: Contexto persistente (mantém login)
- Novo: API REST com FastAPI
- Novo: Integração fácil com n8n

### v1.0.0
- Versão inicial (só scraping básico)

## 📄 License

MIT
