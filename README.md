# scraperOfertas

Projeto de scraping do Mercado Livre com arquitetura em camadas (Clean/DDD na pratica), Playwright, FastAPI, PostgreSQL e Redis.

## Estrutura principal

```text
src/                      # dominio, aplicacao, infraestrutura e apresentacao
apps/                     # entrypoints executaveis (API/GUI/pipeline/scheduler/scraper)
db/                       # alembic + SQL de referencia
config/                   # env e dependencias python
deploy/                   # Dockerfile e compose
scripts/                  # scripts operacionais (windows/linux)
docs/                     # documentacao funcional
tests/                    # testes
```

## Entrypoints oficiais

- GUI: `python -m apps.gui.main`
- API: `uvicorn apps.api.main:app --host 0.0.0.0 --port 8000`
- Pipeline: `python -m apps.pipeline.main --max-produtos 30 --headless`
- Scheduler: `python -m apps.scheduler.main --intervalo 30 --produtos 30 --job-timeout-seconds 30`
- Scraper manual: `python -m apps.scraper.main`
- Login local/cookies: `python -m apps.scraper.login_local`

Os arquivos antigos de entrypoint na raiz foram removidos por decisao de reorganizacao.

## Setup rapido

```bash
pip install -r config/python/requirements.txt
playwright install chromium
```

Crie `config/env/.env` a partir de `config/env/.env.example`.

## Banco e migracoes

```bash
alembic -c db/alembic.ini upgrade head
```

## Docker local

```bash
docker compose -f deploy/docker/docker-compose.local.yml up -d --build
```

## Docs

- `docs/README_REFACTOR.md`
- `docs/README_GUI.md`
- `docs/README_PIPELINE.md`
