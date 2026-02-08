# 🌐 Scripts VPS

Scripts para deploy e gerenciamento no servidor VPS (72.60.51.81).

---

## ⚠️ Ambiente Principal: LOCAL

**Atenção:** O ambiente principal agora é **LOCAL** (docker-compose.local.yml).

Estes scripts VPS são mantidos para:
- ✅ Deploy em produção (opcional)
- ✅ Backup / fallback
- ✅ Testes de staging

---

## 📝 Scripts Disponíveis

### 1. `deploy_vps_test.ps1`
Deploy completo para VPS com teste automático.

```powershell
.\vps\deploy_vps_test.ps1
```

**O que faz:**
1. Build da imagem Docker
2. Push para Docker Hub (eduardogubert/scraperofertas)
3. Deploy no VPS via SSH
4. Testa scraping com 2 produtos
5. Analisa logs

**Pré-requisitos:**
- Docker rodando local
- Acesso SSH ao VPS (root@72.60.51.81)
- Cookies ML sincronizados

---

### 2. `sync_to_vps.ps1`
Sincroniza cookies locais para VPS.

```powershell
.\vps\sync_to_vps.ps1
```

**O que faz:**
1. Compacta `ml_browser_data/` local
2. Envia via SCP para VPS
3. Extrai no VPS
4. Reinicia serviço Docker

**Quando usar:**
- Após `python login_local.py`
- Quando cookies expirarem no VPS

---

### 3. `configure_proxy.ps1`
Configura proxy residencial no VPS.

```powershell
.\vps\configure_proxy.ps1
```

**O que faz:**
1. Solicita credenciais do proxy
2. Cria/atualiza `.env` no VPS
3. Atualiza `docker-compose.yml` com proxy
4. Redeploy do stack

**Quando usar:**
- ML bloqueando IP do VPS (account-verification)
- Necessidade de IP residencial

---

### 4. `rebuild_and_deploy.ps1`
Rebuild completo e deploy.

```powershell
.\vps\rebuild_and_deploy.ps1
```

**O que faz:**
1. Build sem cache (`--no-cache`)
2. Push para Docker Hub
3. Pull no VPS
4. Restart do serviço

**Quando usar:**
- Após mudanças no código
- Problemas com cache Docker
- Deploy de nova versão

---

## 🔧 Configuração VPS

### Servidor
- **IP:** 72.60.51.81
- **User:** root
- **Password:** B@ruck151022#@

### Docker Swarm
- **Stack:** scraperofertas
- **Service:** scraperofertas_scraper-ml-afiliado
- **Image:** eduardogubert/scraperofertas:latest

### Arquivos no VPS
```
/root/scraperofertas/
├── docker-compose.scraperofertas.yml
├── .env (com PROXY_SERVER, PROXY_USER, PROXY_PASS)
└── ml_browser_data/ (cookies sincronizados)
```

---

## 📊 Verificações VPS

### Status do serviço
```powershell
ssh root@72.60.51.81 "docker service ps scraperofertas_scraper-ml-afiliado"
```

### Logs
```powershell
ssh root@72.60.51.81 "docker service logs --tail 100 scraperofertas_scraper-ml-afiliado"
```

### Health check
```powershell
curl -k https://scraperofertas.soluztions.shop/health
```

### Status de cookies
```powershell
curl -k https://scraperofertas.soluztions.shop/auth/status
```

---

## 🔄 Workflow: Local → VPS

1. **Desenvolvimento local** (docker-compose.local.yml)
2. **Teste local** (`.\diagnose-local.ps1`)
3. **Build e push** (`.\vps\rebuild_and_deploy.ps1`)
4. **Deploy VPS** (automático no script)
5. **Sincronizar cookies** (`.\vps\sync_to_vps.ps1`)
6. **Validar** (curl health + auth/status)

---

## 💡 Dicas

### Quando usar VPS vs Local?

| Aspecto | 🏠 Local | ☁️ VPS |
|---------|---------|-------|
| **Desenvolvimento** | ✅ Recomendado | ❌ |
| **Testes** | ✅ Rápido | ⏱️ Lento |
| **Produção 24/7** | ❌ PC precisa ficar ligado | ✅ Always-on |
| **IP Residencial** | ✅ Automático | ❌ Precisa proxy |
| **Custos** | ✅ Grátis | 💰 VPS + Proxy |

### Recomendação Atual

🎯 **Use LOCAL para:**
- Desenvolvimento e testes
- Execução diária (3x ao dia)
- Menor custo (sem proxy necessário)

☁️ **Use VPS apenas se:**
- Precisa disponibilidade 24/7
- Tem proxy residencial configurado
- Quer backup/redundância

---

## 🐛 Troubleshooting VPS

### Serviço não inicia
```powershell
ssh root@72.60.51.81 "docker service logs scraperofertas_scraper-ml-afiliado"
```

### Account-verification no VPS
→ Configure proxy: `.\vps\configure_proxy.ps1`

### Cookies expirados
→ Sincronize: `.\vps\sync_to_vps.ps1`

### Imagem não atualiza
```powershell
ssh root@72.60.51.81 "docker service update --force --image eduardogubert/scraperofertas:latest scraperofertas_scraper-ml-afiliado"
```

---

**Voltar:** [README principal](../README.md)
