# Pipeline de Scraping ML com Banco de Dados

Pipeline completo que executa scraping de ofertas do Mercado Livre e salva os dados em PostgreSQL, evitando duplicatas.

## 🚀 Configuração Inicial

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurar Banco de Dados
```bash
# Copiar template de configuração
cp .env.example .env

# Editar com suas credenciais
notepad .env  # Windows
nano .env     # Linux/Mac
```

### 3. Criar Schema no Banco (PostgreSQL)
```bash
psql -h SEU_HOST -U SEU_USER -d SEU_DB -f sql/postgresql.sql
```

## 📋 Como Usar

### Execução com Argumentos CLI
```bash
# Processar 50 produtos
python pipeline.py --max-produtos 50

# Processar 10 produtos (para teste)
python pipeline.py --max-produtos 10
```

### Execução Interativa
```bash
# O programa pergunta quantos produtos processar
python pipeline.py
```

## 📊 Relatórios

O pipeline gera relatórios detalhados:
- ✅ Novos produtos salvos
- ⏭️ Produtos já existentes (pulados)
- ❌ Erros durante processamento

## 📁 Estrutura de Arquivos

```
├── pipeline.py          # 🎯 Entrypoint principal
├── database.py          # 💾 Gerenciamento de banco
├── utils.py             # 🛠️ Utilitários de normalização
├── scraper_ml_afiliado.py # 🤖 Scraper existente (reutilizado)
├── .env.example         # ⚙️ Template de configuração
├── requirements.txt     # 📦 Dependências Python
└── sql/
    ├── postgresql.sql   # 🐘 Schema PostgreSQL
    └── mysql.sql        # 🐬 Schema MySQL (alternativa)
```

## 🔧 Configurações Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|---------|
| `DB_HOST` | Servidor PostgreSQL | `localhost` |
| `DB_PORT` | Porta do banco | `5432` |
| `DB_NAME` | Nome da database | *(obrigatório)* |
| `DB_USER` | Usuário do banco | *(obrigatório)* |
| `DB_PASS` | Senha do banco | *(obrigatório)* |
| `SCRAPER_HEADLESS` | Executar sem interface | `false` |
| `SCRAPER_WAIT_MS` | Delay entre ações (ms) | `1500` |

## 📝 Logs

- Console: Progresso em tempo real
- Arquivo: `pipeline_YYYYMMDD.log`

## 🔍 Consultas Úteis

```sql
-- Total de produtos hoje
SELECT COUNT(*) FROM ml_ofertas WHERE created_at::date = CURRENT_DATE;

-- Produtos com maior desconto
SELECT nome, desconto, preco_atual 
FROM ml_ofertas 
WHERE desconto > 50 
ORDER BY desconto DESC 
LIMIT 10;

-- Estatísticas gerais
SELECT * FROM vw_stats_diarias LIMIT 7;
```

## ⚠️ Solução de Problemas

### Erro de Conexão com Banco
```
❌ Erro ao conectar banco: connection refused
```
**Solução**: Verifique credenciais no `.env` e conectividade com servidor.

### Variáveis de Ambiente Faltando
```
❌ Variáveis de ambiente faltando: ['DB_HOST', 'DB_NAME']
```
**Solução**: Configure todas as variáveis obrigatórias no `.env`.

### Browser Não Abre
```
⚠️ Não conseguiu extrair link de afiliado
```
**Solução**: Configure `SCRAPER_HEADLESS=false` no `.env` para debug.