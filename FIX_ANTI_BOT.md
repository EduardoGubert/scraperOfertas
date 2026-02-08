# 🔧 FIX: Detecção Anti-Bot no Servidor

## Problema Identificado

O Mercado Livre estava detectando o navegador headless no servidor e bloqueando o acesso às páginas de produtos. 

**Sintomas:**
- ✅ Login funcionando
- ✅ Página de ofertas carregando
- ❌ Páginas de produtos não renderizando
- ❌ Botão "Compartilhar" não encontrado

## Soluções Implementadas

### 1. ✅ Xvfb (Display Virtual Real)
**Arquivo:** `Dockerfile`

Agora o Xvfb é iniciado **antes** do Uvicorn, criando um display virtual real onde o Chrome pode renderizar páginas.

```dockerfile
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & sleep 2 && uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000"]
```

**Por que funciona:** Sites anti-bot checam se há um contexto gráfico real. Sem Xvfb, o browser roda "cego".

### 2. ✅ Screenshots de Debug
**Arquivo:** `scraper_ml_afiliado.py`

Adicionado captura automática de screenshots ao acessar produtos:

```python
screenshot_path = f"/app/debug_produto_{timestamp}.png"
await self.page.screenshot(path=screenshot_path, full_page=False)
```

**Como acessar:**
```bash
# Via SSH
ssh root@72.60.51.81
docker exec -it $(docker ps -qf name=scraperofertas_scraper) ls -lh /app/debug_*.png

# Copiar para análise local
scp root@72.60.51.81:/app/debug_*.png .
```

### 3. ✅ User Agent Correto
**Arquivo:** `scraper_ml_afiliado.py`

Detecta o ambiente e usa o user agent apropriado:

- **Docker (Linux):** `Mozilla/5.0 (X11; Linux x86_64) ...`
- **Local (Windows):** `Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...`

**Por que funciona:** Sites checam consistência entre user agent e plataforma real.

### 4. ✅ Flags Adicionais de Rendering
**Arquivo:** `scraper_ml_afiliado.py`

```python
'--use-gl=swiftshader',  # Software rendering para Docker
'--disable-software-rasterizer',
```

Melhora o rendering de páginas em ambientes sem GPU.

## 🚀 Deploy

### Automático (Recomendado)
```powershell
.\rebuild_and_deploy.ps1
```

### Manual
```powershell
# 1. Build
docker build -t eduardopoa/scraper-ml-afiliado:latest .

# 2. Push
docker push eduardopoa/scraper-ml-afiliado:latest

# 3. Deploy na VPS
ssh root@72.60.51.81 "docker pull eduardopoa/scraper-ml-afiliado:latest && docker service update --image eduardopoa/scraper-ml-afiliado:latest --force scraperofertas_scraper-ml-afiliado"
```

## 🔍 Verificação

### 1. Status do Auth
```powershell
curl.exe -k https://scraperofertas.soluztions.shop/auth/status -H 'X-API-Key: egn-2025-secret-key'
```

### 2. Testar Scraping
```powershell
curl.exe -k https://scraperofertas.soluztions.shop/scrape -H 'X-API-Key: egn-2025-secret-key' -H 'Content-Type: application/json' -d '{\"max_produtos\": 3}'
```

### 3. Ver Logs
```bash
ssh root@72.60.51.81
docker service logs scraperofertas_scraper-ml-afiliado --tail 100 -f
```

### 4. Analisar Screenshots
```bash
# Listar screenshots
ssh root@72.60.51.81 'docker exec -it $(docker ps -qf name=scraperofertas_scraper) ls -lh /app/debug_*.png'

# Copiar para local
scp root@72.60.51.81:/app/debug_produto_*.png ./debug/

# Ou via Portainer
# Console do container → File Browser → /app/debug_*.png
```

## 📊 Checklist Pós-Deploy

- [ ] Serviço subiu sem erros
- [ ] Auth status retorna `cookies_valid: true`
- [ ] Teste de scraping retorna produtos com links de afiliado
- [ ] Screenshots salvos (check via SSH ou Portainer)
- [ ] Screenshots mostram páginas renderizadas (não em branco)
- [ ] Botão "Compartilhar" é encontrado

## 🐛 Debug

Se ainda houver problemas:

1. **Verificar Xvfb está rodando:**
```bash
ssh root@72.60.51.81
docker exec -it $(docker ps -qf name=scraperofertas_scraper) ps aux | grep Xvfb
```

2. **Ver screenshots:**
- Se estão em branco → problema de rendering
- Se mostram erro → problema de anti-bot
- Se parecem normais → problema nos seletores

3. **Testar em modo não-headless (temporário):**
No `api_ml_afiliado.py`, mude `headless=True` para `headless=False` e veja os logs.

## 📝 Notas Técnicas

- **Xvfb:** Cria display virtual em :99 com resolução 1920x1080x24
- **Sleep 2:** Aguarda Xvfb inicializar antes do Uvicorn
- **Screenshots:** Salvos em `/app/` com timestamp
- **Persistência:** ml_browser_data é volume Docker (cookies persistem)

## ⏭️ Próximos Passos (se necessário)

Se os problemas persistirem:

1. **Testar com Chromium mais recente:** Atualizar versão no Dockerfile
2. **Adicionar stealth plugin:** `playwright-stealth` para mascarar melhor
3. **Proxy rotativo:** Evitar rate limiting do ML
4. **Aumentar delays:** `wait_ms` maior entre ações
