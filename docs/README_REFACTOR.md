# README Refactor

## Estrutura alvo aplicada

```text
src/
apps/
  api/main.py
  gui/main.py
  pipeline/main.py
  scheduler/main.py
  scraper/main.py
  scraper/login_local.py
db/
  alembic.ini
  alembic/
  sql/
config/
  env/
  python/
deploy/
  docker/
scripts/
  windows/
  linux/
docs/
tests/
```

## Variaveis de ambiente principais

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`
- `CACHE_BACKEND` (`redis` ou `json`)
- `CACHE_TTL_SECONDS` (default `86400`)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_SSL`
- `SCHEDULER_INTERVAL_MINUTES` (default `30`)
- `SCHEDULER_MAX_PRODUTOS` (default `30`)
- `SCHEDULER_JOB_TIMEOUT_SECONDS` (default `30`)
- `SCRAPER_API_KEY`
- `APP_TIMEZONE` (default `America/Sao_Paulo`)

## Comandos oficiais

```bash
# API
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Scheduler (uma rodada)
python -m apps.scheduler.main --agora

# Scheduler continuo
python -m apps.scheduler.main --intervalo 30 --produtos 30 --job-timeout-seconds 30

# Pipeline
python -m apps.pipeline.main --max-produtos 30 --headless

# GUI
python -m apps.gui.main

# Login local / export cookies
python -m apps.scraper.login_local

# Migracoes
alembic -c db/alembic.ini upgrade head
```

## Jobs disponiveis

- `ofertas`
- `ofertas_relampago`
- `cupons`
- `todos` (sequencia: ofertas -> ofertas_relampago -> cupons)

## Endpoints

- `POST /scrape/ofertas`
- `POST /scrape/ofertas/relampago`
- `POST /scrape/cupons`
- `POST /scrape/todos`
