# 🛡️ Configurações Anti-Bot Implementadas

## 🎯 Objetivo
Contornar o bloqueio de verificação de conta do Mercado Livre usando 3 estratégias combinadas.

---

## ✅ Otimizações Implementadas

### 1️⃣ **Chrome Real ao invés de Chromium**
**Por que?** Chrome real tem menos assinaturas de automação detectáveis.

**Como usar:**
```python
from scraper_ml_afiliado import ScraperMLAfiliado

async with ScraperMLAfiliado(
    use_chrome=True,  # Usa Chrome real (padrão)
    headless=False
) as scraper:
    # ... seu código
```

**No Docker:** Não tem Chrome instalado, usa Chromium automaticamente.

---

### 2️⃣ **Suporte a Proxy (IP Residencial Recomendado)**
**Por que?** IP da VPS pode estar marcado. Use proxy residencial brasileiro.

**Como configurar:**

#### **Sem autenticação:**
```python
async with ScraperMLAfiliado(
    proxy={
        'server': 'http://proxy-brasileiro.com:8080'
    }
) as scraper:
    # ... seu código
```

#### **Com autenticação (username/password):**
```python
async with ScraperMLAfiliado(
    proxy={
        'server': 'http://proxy-residencial.com:8080',
        'username': 'seu_usuario',
        'password': 'sua_senha'
    }
) as scraper:
    # ... seu código
```

#### **Provedores Recomendados:**
- **Bright Data:** https://brightdata.com (melhor qualidade)
- **Oxylabs:** https://oxylabs.io
- **Smartproxy:** https://smartproxy.com
- **Luminati/NetNut:** IPs residenciais brasileiros

**Dica:** Escolha proxy **residencial brasileiro** para parecer usuário real do Brasil.

---

### 3️⃣ **Navegação Humana Antes de Acessar Produtos**
**Por que?** Acesso direto a produtos parece bot. Simulamos comportamento humano.

**O que faz:**
1. Visita home do ML primeiro
2. Scroll na página (simula leitura)
3. Move mouse aleatoriamente
4. Navega para Ofertas (caminho natural)
5. Explora ofertas antes de clicar em produtos
6. Delays aleatórios entre ações (1.5s a 5s)

**Execução automática:** Roda sozinha na primeira vez que buscar produtos.

---

## 🚀 Exemplo Completo

### **Local (Windows - COM Chrome Real e Proxy):**
```python
import asyncio
from scraper_ml_afiliado import ScraperMLAfiliado

async def main():
    # Configuração completa anti-bot
    async with ScraperMLAfiliado(
        headless=False,  # Mostra navegador
        use_chrome=True,  # Chrome real
        proxy={
            'server': 'http://proxy-brasil.com:8080',
            'username': 'meu_user',
            'password': 'minha_senha'
        },
        max_produtos=10
    ) as scraper:
        # Verifica login
        if not await scraper.verificar_login():
            await scraper.fazer_login_manual()
        
        # Busca produtos (navegação humana automática)
        links = await scraper.obter_links_ofertas()
        
        # Processa produtos
        for link in links:
            produto = await scraper.extrair_dados_produto(link)
            print(f"✅ {produto['nome']}: {produto['url_curta']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### **Docker (VPS - COM Proxy):**
```python
# Dockerfile já configurado para usar Chromium + Xvfb
# Adicione proxy via variável de ambiente ou código:

async with ScraperMLAfiliado(
    headless=True,
    use_chrome=False,  # Chromium no Docker (Chrome não está instalado)
    proxy={
        'server': os.getenv('PROXY_SERVER'),  # http://ip:porta
        'username': os.getenv('PROXY_USER'),
        'password': os.getenv('PROXY_PASS')
    }
) as scraper:
    # ... seu código
```

---

## 🔧 Como Testar Localmente

### **1. Teste SEM Proxy (para verificar Chrome real):**
```bash
python login_local.py  # Faz login e salva cookies
python -c "
import asyncio
from scraper_ml_afiliado import ScraperMLAfiliado

async def test():
    async with ScraperMLAfiliado(
        use_chrome=True,
        headless=False
    ) as scraper:
        links = await scraper.obter_links_ofertas()
        print(f'Testado: {len(links)} produtos encontrados')
        
        # Testa 1 produto
        if links:
            p = await scraper.extrair_dados_produto(links[0])
            print(f'Produto: {p[\"nome\"]}')
            print(f'Link: {p[\"url_curta\"]}')

asyncio.run(test())
"
```

### **2. Teste COM Proxy:**
```bash
# Edite test_proxy.py (criar arquivo):
cat > test_proxy.py << 'EOF'
import asyncio
from scraper_ml_afiliado import ScraperMLAfiliado

async def test():
    async with ScraperMLAfiliado(
        use_chrome=True,
        headless=False,
        proxy={
            'server': 'http://SEU_PROXY:PORTA',  # <<<< EDITAR AQUI
            'username': 'usuario',  # <<<< EDITAR SE NECESSÁRIO
            'password': 'senha'     # <<<< EDITAR SE NECESSÁRIO
        }
    ) as scraper:
        # Verifica IP do proxy
        await scraper.page.goto('https://api.ipify.org?format=json')
        await scraper._human_delay(1000, 2000)
        
        content = await scraper.page.content()
        print(f"🌐 IP detectado: {content}")
        
        # Testa scraping
        links = await scraper.obter_links_ofertas()
        print(f"✅ {len(links)} produtos encontrados")

asyncio.run(test())
EOF

python test_proxy.py
```

---

## 📊 Resultados Esperados

### **Antes (sem otimizações):**
```
❌ Redirect para: https://www.mercadolivre.com.br/gz/account-verification
❌ 0 produtos com link de afiliado
```

### **Depois (com otimizações):**
```
✅ Navegação humana concluída
✅ Usando Chrome REAL
✅ Usando PROXY: http://proxy-brasil:8080
✅ 10 produtos extraídos com sucesso
✅ Links de afiliado funcionando
```

---

## 🐳 Deploy no Docker com Proxy

### **docker-compose.yml:**
```yaml
services:
  scraper-ml-afiliado:
    # ... configuração existente
    environment:
      - PROXY_SERVER=http://seu-proxy:8080
      - PROXY_USER=seu_usuario
      - PROXY_PASS=sua_senha
```

### **api_ml_afiliado.py:**
```python
# Adicione no __init__ ou configure_scraper:
proxy_config = None
if os.getenv('PROXY_SERVER'):
    proxy_config = {
        'server': os.getenv('PROXY_SERVER'),
    }
    if os.getenv('PROXY_USER'):
        proxy_config['username'] = os.getenv('PROXY_USER')
        proxy_config['password'] = os.getenv('PROXY_PASS')

async with ScraperMLAfiliado(
    proxy=proxy_config,
    use_chrome=False,  # Docker usa Chromium
    headless=True
) as scraper:
    # ... seu código
```

---

## 🎯 Checklist de Deploy

- [ ] **Chrome Real instalado** (local) ou Chromium (Docker)
- [ ] **Proxy residencial brasileiro** configurado
- [ ] **Cookies válidos** (login feito com `login_local.py`)
- [ ] **Xvfb rodando** (Docker) ou X11 (local)
- [ ] **Delays entre requisições** (2-5 segundos aleatórios)
- [ ] **Navegação humana ativa** (automática no código)

---

## 🆘 Troubleshooting

### **Problema: Ainda sendo bloqueado**
**Soluções:**
1. Verifique se proxy está funcionando: `curl --proxy http://seu-proxy:porta https://api.ipify.org`
2. Use proxy residencial (não datacenter)
3. Aumente delays: `wait_ms=3000`
4. Rode headless=False local para ver o que está acontecendo

### **Problema: Proxy não conecta**
**Soluções:**
1. Teste proxy fora do script: `curl --proxy http://ip:porta https://google.com`
2. Verifique firewall da VPS
3. Confirme formato correto: `http://user:pass@ip:porta`

### **Problema: Chrome não encontrado (local)**
**Soluções:**
1. Instale Chrome: https://www.google.com/chrome/
2. Ou use `use_chrome=False` para usar Chromium
3. Playwright auto-instala Chromium se Chrome não existir

---

## 📈 Monitoramento

Logs indicam status das otimizações:
```
🚀 Usando Chrome REAL (menos detectável)
🌐 Usando PROXY: http://proxy-brasil:8080 (IP residencial recomendado)
🤖 Simulando navegação HUMANA (anti-bot)...
  ✅ Navegação humana concluída!
```

⚠️ Se ver isso, proxy NÃO está funcionando:
```
⚠️ Usando Chromium (mais detectável, considere usar Chrome real)
```

---

## 🔗 Links Úteis

- **Playwright Proxy Docs:** https://playwright.dev/python/docs/network#http-proxy
- **API Proxy Residential:** https://brightdata.com/products/residential-proxies
- **ML Anti-Bot Info:** Interno (documentado em FIX_ANTI_BOT.md)

---

Última atualização: 8 de fevereiro de 2026
