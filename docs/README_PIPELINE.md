# Pipeline scraperOfertas

Pipeline para rodar scraping e persistencia com deduplicacao em PostgreSQL + cache.

## Setup

```bash
pip install -r config/python/requirements.txt
playwright install chromium
```

Crie `config/env/.env` a partir de `config/env/.env.example`.

## Migracao de banco

```bash
alembic -c db/alembic.ini upgrade head
```

## Executar

### CLI

```bash
# Processar 50 itens
python -m apps.pipeline.main --max-produtos 50 --headless

# Processar 10 itens
python -m apps.pipeline.main --max-produtos 10 --headless
```

### Interativo

```bash
python -m apps.pipeline.main
```

## Estrutura relevante

```text
apps/pipeline/main.py
src/application/use_cases/run_scraper_job.py
src/infrastructure/persistence/
src/infrastructure/cache/
src/infrastructure/scraping/
```

## Consultas uteis

```sql
SELECT COUNT(*) FROM ml_ofertas WHERE created_at::date = CURRENT_DATE;

SELECT nome, desconto, preco_atual
FROM ml_ofertas
WHERE desconto > 50
ORDER BY desconto DESC
LIMIT 10;
```
