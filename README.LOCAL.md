# 🏠 Ambiente Local - egnOfertas

Configuração completa para rodar todo o sistema **localmente** na sua máquina Windows.

## 📦 O que está incluído?

1. **PostgreSQL 15** - Banco de dados com todas as tabelas
2. **n8n** - Plataforma de automação (workflows)
3. **Scraper ML Afiliado** - API de scraping com Chrome/Chromium

## 🚀 Início Rápido

### 1. Iniciar ambiente

```powershell
.\start-local.ps1
```

Aguarde 2-5 minutos (primeira vez demora mais - instalando Chrome).

### 2. Fazer login no Mercado Livre

```powershell
python login_local.py
```

Faça login quando o navegador abrir.

### 3. Acessar n8n

Abra: http://localhost:5678

- **User:** admin
- **Password:** egn2025admin

### 4. Importar workflow

1. No n8n, clique em **"Import from File"**
2. Selecione: `egnOfertas - ML Promoções WhatsApp v2 (Scraper Direto).json`
3. Configure as variáveis no nó **"⚙️ Configurações"**:

```javascript
scraper_url: "http://scraper-ml-afiliado:8000"
scraper_api_key: "egn-2025-secret-key"

// Evolution API (do servidor remoto)
evolution_url: "https://evolution.soluztions.shop"
evolution_api_key: "7177bcb5d4b424d60f82dfd42f3ef758"
evolution_instance: "EGNOFERTAS"
whatsapp_group_jid: "120363422005501838@g.us"  // SEU JID DO GRUPO
```

### 5. Ativar workflow

Clique em **"Active"** no topo do workflow.

## 📊 Serviços Disponíveis

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **n8n** | http://localhost:5678 | admin / egn2025admin |
| **Scraper API** | http://localhost:8000 | API Key: egn-2025-secret-key |
| **Scraper Docs** | http://localhost:8000/docs | - |
| **PostgreSQL** | localhost:5432 | egn_user / egn_password_2025 |

## 🔧 Comandos Úteis

### Ver logs em tempo real

```powershell
docker compose -f docker-compose.local.yml logs -f
```

### Ver log de um serviço específico

```powershell
# Scraper
docker compose -f docker-compose.local.yml logs -f scraper-ml-afiliado

# n8n
docker compose -f docker-compose.local.yml logs -f n8n

# PostgreSQL
docker compose -f docker-compose.local.yml logs -f postgres
## 📝 Comandos Úteis

### 🔍 Diagnóstico completo

```powershell
.\diagnose-local.ps1
```

Mostra status de todos os containers, logs, conectividade e cookies.

### 🔄 Renovar login ML

```powershell
# Com confirmação
.\renew-login.ps1

# Automático (sem perguntar)
.\renew-login.ps1 -Auto
```

### 🔄 Sincronizar cookies

```powershell
.\sync-cookies-local.ps1
```

### Ver logs em tempo real

```powershell
# Todos os serviços
docker compose -f docker-compose.local.yml logs -f

# Apenas Scraper
docker logs -f egn_scraper_local

# Apenas n8n
docker logs -f egn_n8n_local

# Apenas PostgreSQL
docker logs -f egn_postgres_local
```

### Gerenciar serviços

```powershell
# Parar todos
.\stop-local.ps1

# Reiniciar um serviço
docker restart egn_scraper_local

# Ver status
docker ps --filter "name=egn_"
```

### Acessar containers

```powershell
# PostgreSQL
docker exec -it egn_postgres_local psql -U egn_user -d egn_ofertas

# Scraper (shell)
docker exec -it egn_scraper_local sh

# Ver screenshots de debug
docker exec -it egn_scraper_local ls -lh /app/debug_screenshots/
```

## 🗄️ Banco de Dados

### Conectar via DBeaver/pgAdmin

- **Host:** localhost
- **Port:** 5432
- **Database:** egn_ofertas
- **User:** egn_user
- **Password:** egn_password_2025

### Tabelas criadas automaticamente

1. **egn_ml_tokens** - Tokens OAuth do ML
2. **egn_products** - Produtos scrapados
3. **egn_send_log** - Log de envios WhatsApp

### Views úteis

```sql
-- Ver produtos pendentes de envio
SELECT * FROM v_produtos_pendentes;

-- Estatísticas
SELECT * FROM v_stats_produtos;
```

## 🧪 Testar Scraper

### Via curl (PowerShell)

```powershell
# Health check
curl http://localhost:8000/health

# Verificar login
curl -H "X-API-Key: egn-2025-secret-key" http://localhost:8000/auth/status

# Scraping de teste (2 produtos)
curl -X POST http://localhost:8000/scrape/ofertas `
  -H "X-API-Key: egn-2025-secret-key" `
  -H "Content-Type: application/json" `
  -d '{"max_produtos": 2, "headless": true}'
```

### Via navegador

Abra: http://localhost:8000/docs

## 🐛 Troubleshooting

### Scraper não encontra botão "Compartilhar"

Provavelmente caindo na tela de account-verification. O bypass já está implementado, mas se persistir:

1. Verifique se Chrome foi instalado (logs devem mostrar "🚀 Usando Chrome REAL")
2. Se não, tente forçar rebuild:
   ```powershell
   docker compose -f docker-compose.local.yml build --no-cache scraper-ml-afiliado
   ```

### PostgreSQL não inicia

```powershell
# Ver logs
docker compose -f docker-compose.local.yml logs postgres

# Remover volume e recriar
docker compose -f docker-compose.local.yml down -v
.\start-local.ps1
```

### n8n não conecta ao PostgreSQL

Aguarde 30 segundos após `start-local.ps1`. O n8n espera PostgreSQL estar 100% pronto.

### Porta já em uso

Se alguma porta (5432, 5678, 8000) já estiver em uso, edite `docker-compose.local.yml`:

```yaml
ports:
  - "5433:5432"  # Mude 5432 para 5433
```

## 📝 Configurações Avançadas

### Usar proxy residencial

Edite `.env.local`:

```env
PROXY_SERVER=http://IP:PORTA
PROXY_USER=seu_usuario
PROXY_PASS=sua_senha
```

Reinicie:

```powershell
docker compose -f docker-compose.local.yml restart scraper-ml-afiliado
```

### Aumentar timeout do scraper

Edite `docker-compose.local.yml`, adicione em `scraper-ml-afiliado`:

```yaml
environment:
  SCRAPER_TIMEOUT: 900000  # 15 minutos
```

## 🔄 Atualizar código do scraper

Após modificar `scraper_ml_afiliado.py` ou `api_ml_afiliado.py`:

```powershell
docker compose -f docker-compose.local.yml build scraper-ml-afiliado
docker compose -f docker-compose.local.yml up -d scraper-ml-afiliado
```

## 🧹 Limpeza Total

Remove TUDO (containers, volumes, dados):

```powershell
docker compose -f docker-compose.local.yml down -v
Remove-Item -Recurse -Force debug_screenshots
```

## 📱 Evolution API (Remota)

A Evolution API continua no servidor remoto. Não precisa rodar localmente.

**Configuração no workflow n8n:**
- URL: `https://evolution.soluztions.shop`
- API Key: `7177bcb5d4b424d60f82dfd42f3ef758`
- Instance: `EGNOFERTAS`

## ✅ Checklist de Setup

- [ ] `.\start-local.ps1` executado com sucesso
- [ ] Todos os containers rodando: `.\diagnose-local.ps1`
- [ ] Login ML feito: `python login_local.py`
- [ ] Cookies sincronizados: `.\sync-cookies-local.ps1`
- [ ] n8n acessível em http://localhost:5678
- [ ] Credencial PostgreSQL configurada no n8n (host: `postgres`)
- [ ] Workflow importado e configurado
- [ ] Teste de scraping: `curl http://localhost:8000/auth/status`
- [ ] PostgreSQL com dados de produtos
- [ ] Evolution API testada (envio para WhatsApp)

## 🔄 Renovação Automática de Login

Quando o workflow detectar que os cookies expiraram, ele pode chamar automaticamente:

```powershell
.\renew-login.ps1 -Auto
```

Ou você pode configurar no n8n um nó que chama este script quando `cookies_valid = false`.

**Fluxo automático:**
1. n8n detecta cookies expirados via `/auth/status`
2. n8n chama webhook/comando que executa `renew-login.ps1 -Auto`
3. Script abre browser, você faz login
4. Cookies salvos automaticamente
5. Container reiniciado
6. Workflow continua normalmente

## 📞 Suporte

Se algo der errado:

1. Ver logs: `docker compose -f docker-compose.local.yml logs -f`
2. Verificar containers: `docker compose -f docker-compose.local.yml ps`
3. Reiniciar: `.\stop-local.ps1` + `.\start-local.ps1`
