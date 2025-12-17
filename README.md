# 🛒 Scraper Ofertas

API para web scraping de e-commerces brasileiros com suporte a JavaScript rendering.

## ✨ Features

- **Sites suportados:** Magazine Você, Magalu, Mercado Livre, Shopee, Amazon Brasil
- **JavaScript Rendering:** Usa Playwright (Chromium headless)
- **Anti-detecção:** Remove flags de webdriver, user-agent realista
- **Lazy loading:** Scroll automático para carregar todos os produtos
- **API REST:** Integração fácil com n8n, Make, Zapier

## 🚀 Quick Start

### Docker (Recomendado)

```bash
# Pull da imagem
docker pull ghcr.io/eduardogubertpersonal/scraperofertas:latest

# Rodar
docker run -d -p 8000:8000 ghcr.io/eduardogubertpersonal/scraperofertas:latest
```

### Local

```bash
pip install -r requirements.txt
playwright install chromium

# Rodar API
uvicorn api_scraper:app --host 0.0.0.0 --port 8000

# Ou rodar script direto
python scraper_ofertas.py
```

## 📡 API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Info da API |
| GET | `/health` | Health check |
| POST | `/scrape` | Auto-detecta o site |
| POST | `/scrape/magazine` | Magazine Você / Magalu |
| POST | `/scrape/mercadolivre` | Mercado Livre |
| POST | `/scrape/shopee` | Shopee |
| POST | `/scrape/amazon` | Amazon Brasil |

### Request Body

```json
{
  "url": "https://www.magazinevoce.com.br/magazinegubert/selecao/ofertasdodia/",
  "wait_ms": 1500,
  "headless": true
}
```

### Response

```json
{
  "success": true,
  "total": 60,
  "produtos": [
    {
      "foto": "https://...",
      "nome": "Jogo de Panelas...",
      "preço": "R$ 899,90",
      "url": "https://..."
    }
  ],
  "scraped_at": "2024-01-15T10:30:00",
  "source_url": "https://..."
}
```

## 🔧 Integração com n8n

### Via HTTP Request Node

**URL:** `http://scraper:8000/scrape` (rede interna Docker)

**Ou:** `https://scraperofertas.soluztions.shop/scrape` (externo)

**Method:** POST

**Body:**
```json
{
  "url": "{{ $json.url }}",
  "wait_ms": 2000
}
```

### Exemplo de Workflow

1. **Schedule Trigger** → Executa a cada hora
2. **HTTP Request** → Chama `/scrape` com URL das ofertas
3. **Filter** → Filtra produtos por preço/desconto
4. **Send Message** → Envia para WhatsApp/Telegram

## 🐳 Deploy com Docker Swarm + Traefik

```bash
# Na sua VPS
docker stack deploy -c docker-compose.yml scraper
```

O `docker-compose.yml` já está configurado com:
- Labels do Traefik para HTTPS automático
- Rede `traefik_default`
- Limite de 2GB de memória (Playwright precisa)

## 📁 Estrutura do Projeto

```
scraperOfertas/
├── scraper_ofertas.py    # Classe principal do scraper
├── api_scraper.py        # API FastAPI
├── requirements.txt      # Dependências Python
├── Dockerfile           # Build da imagem
├── docker-compose.yml   # Deploy Swarm + Traefik
└── .github/
    └── workflows/
        └── docker-build.yml  # CI/CD automático
```

## 🔄 CI/CD

O GitHub Actions builda e publica automaticamente a imagem no GitHub Container Registry a cada push na `main`.

Para atualizar na VPS:

```bash
docker service update --image ghcr.io/eduardogubertpersonal/scraperofertas:latest scraper_scraper
```

## 📝 TODO

- [ ] Suporte a paginação (múltiplas páginas)
- [ ] Cache de resultados (Redis)
- [ ] Rate limiting por IP
- [ ] Webhook para notificações
- [ ] Suporte a mais sites (Casas Bahia, Americanas, AliExpress)

## 📄 License

MIT
