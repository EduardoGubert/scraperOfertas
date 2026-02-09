# scraperOfertas Refactor Guide

## Estrutura

```text
src/
  domain/
    entities/
    interfaces/
    value_objects/
  application/
    dto/
    services/
    use_cases/
  infrastructure/
    cache/
    config/
    logging/
    persistence/
    scraping/
  presentation/
    api/
    gui/
    scheduler/
tests/
alembic/
```

## Variaveis de ambiente principais

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`
- `CACHE_BACKEND` (`redis` ou `json`)
- `CACHE_TTL_SECONDS` (default seguro: `86400`)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_SSL`
- `SCHEDULER_INTERVAL_MINUTES` (default `30`)
- `SCHEDULER_MAX_PRODUTOS` (default `30`)
- `SCHEDULER_JOB_TIMEOUT_SECONDS` (default `30`)
- `SCRAPER_API_KEY`

## Migracoes

```bash
alembic upgrade head
```

## Execucao local

```bash
# API
uvicorn api_ml_afiliado:app --host 0.0.0.0 --port 8000

# Scheduler (uma rodada)
python scheduler_runner.py --agora

# Scheduler continuo
python scheduler_runner.py --intervalo 30 --produtos 30 --job-timeout-seconds 30

# GUI
python gui_scraper.py
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
