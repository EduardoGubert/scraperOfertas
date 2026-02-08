# 🛒 egnOfertas - Scraper ML Afiliado

Sistema automatizado para scraping de ofertas do Mercado Livre com links de afiliado e envio para WhatsApp via n8n.

## 🚀 Início Rápido (Ambiente Local)

### 1. Iniciar serviços
```powershell
.\start-local.ps1
```

### 2. Fazer login no ML
```powershell
python login_local.py
```

### 3. Acessar n8n
- URL: http://localhost:5678
- User: `admin` | Password: `egn2025admin`

### 4. Importar workflow
- Arquivo: `egnOfertas - ML Promoções WhatsApp v2 (Scraper Direto).json`
- Configure o JID do grupo WhatsApp no nó "⚙️ Configurações"

### 5. Ativar workflow
Clique em "Active" no n8n!

---

## 📊 Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **n8n** | http://localhost:5678 | admin / egn2025admin |
| **Scraper** | http://localhost:8000/docs | API Key: egn-2025-secret-key |
| **PostgreSQL** | localhost:5432 | egn_user / egn_password_2025 |

---

## 🔧 Comandos Principais

```powershell
# Ver status de tudo
.\diagnose-local.ps1

# Renovar login ML
.\renew-login.ps1

# Parar tudo
.\stop-local.ps1

# Ver logs
docker logs -f egn_scraper_local
```

---

## 📚 Documentação Completa

- **[README.LOCAL.md](README.LOCAL.md)** - Guia completo do ambiente local
- **[vps/README.md](vps/README.md)** - Scripts para deploy VPS (opcional)
- **[ANTI_BOT_CONFIG.md](ANTI_BOT_CONFIG.md)** - Configurações anti-bot
- **[PROXY_GUIDE.md](PROXY_GUIDE.md)** - Como configurar proxy

---

## 🗂️ Estrutura do Projeto

```
scraperOfertas/
├── 🐳 Docker Local
│   ├── docker-compose.local.yml    # Stack local completo
│   ├── Dockerfile                   # Imagem do scraper
│   ├── init-db.sql                  # Schema PostgreSQL
│   └── .env.local                   # Configurações
│
├── 🤖 Scraper
│   ├── scraper_ml_afiliado.py      # Core do scraper
│   ├── api_ml_afiliado.py          # API FastAPI
│   └── login_local.py              # Login manual
│
├── 📊 n8n Workflow
│   └── egnOfertas - ML Promoções WhatsApp v2.json
│
├── 🔧 Scripts Locais
│   ├── start-local.ps1             # Inicia ambiente
│   ├── stop-local.ps1              # Para ambiente
│   ├── diagnose-local.ps1          # Diagnóstico
│   ├── renew-login.ps1             # Renova login
│   └── sync-cookies-local.ps1      # Sincroniza cookies
│
├── ☁️ Scripts VPS (opcional)
│   ├── deploy_vps_test.ps1         # Deploy para VPS
│   ├── sync_to_vps.ps1             # Sync cookies VPS
│   ├── configure_proxy.ps1         # Config proxy VPS
│   └── rebuild_and_deploy.ps1      # Rebuild VPS
│
└── 📁 Dados
    ├── ml_browser_data/            # Cookies (local ↔ container)
    └── debug_screenshots/          # Screenshots debug
```

---

## ⚡ Features

- ✅ Scraping automatizado de ofertas ML
- ✅ Links de afiliado extraídos automaticamente
- ✅ Filtro por desconto mínimo (configurável)
- ✅ Envio para grupo WhatsApp via n8n
- ✅ Chrome real (menos detectável que Chromium)
- ✅ Bypass automático de account-verification
- ✅ Suporte a proxy residencial (opcional)
- ✅ Renovação automática de login
- ✅ PostgreSQL com histórico de produtos
- ✅ Agendamento via n8n (8h, 14h, 20h)

---

## 🐛 Troubleshooting

### Scraper não inicia
```powershell
.\diagnose-local.ps1
docker logs egn_scraper_local
```

### Cookies expirados
```powershell
.\renew-login.ps1
```

### n8n não conecta PostgreSQL
Credencial no n8n:
- Host: `postgres` (não `localhost`)
- Port: `5432`
- Database: `egn_ofertas`
- User: `egn_user`
- Password: `egn_password_2025`

---

## 📱 Evolution API (Remota)

WhatsApp continua no servidor remoto:
- URL: `https://evolution.soluztions.shop`
- API Key: `7177bcb5d4b424d60f82dfd42f3ef758`
- Instance: `EGNOFERTAS`

---

## 🎯 Próximos Passos

1. ✅ Ambiente local funcionando → Teste completo
2. 🔄 ML bloqueando? → Configure proxy em `.env.local`
3. 📈 Quer escalar? → Deploy na VPS (scripts em `vps/`)

**Sucesso!** 🎉
