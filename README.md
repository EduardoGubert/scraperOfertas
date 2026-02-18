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
- Scheduler (sem cupons): `python -m apps.scheduler.main --intervalo 30 --produtos 30 --job-timeout-seconds 30 --sem-cupons`
- Scheduler (com filtros): `python -m apps.scheduler.main --intervalo 30 --produtos 30 --job-timeout-seconds 300 --min-desconto 30 --min-comissao 10 --categoria "eletronicos, vestuario"`
- Scraper manual: `python -m apps.scraper.main`
- Login local/cookies: `python -m apps.scraper.login_local`

Os arquivos antigos de entrypoint na raiz foram removidos por decisao de reorganizacao.

## Setup rapido

```bash
pip install -r config/python/requirements.txt
playwright install chromium
```

Crie `config/env/.env` a partir de `config/env/.env.example`.

Filtros de ofertas/relampago:
- `OFFERS_MIN_DESCONTO_PERCENT` (padrao `30`)
- `OFFERS_MIN_COMISSAO_PERCENT` (padrao `10`)
- `OFFERS_CATEGORIA_FILTER` (aceita uma ou varias categorias separadas por virgula)
- `OFFERS_GANHOS_XPATH` (padrao `/html/body/div[1]/nav/div/div[3]/div[1]/div/span`)

Regras:
- filtros de desconto/comissao valem apenas para `ofertas` e `ofertas_relampago`;
- filtro de categoria vale apenas para `ofertas` e `ofertas_relampago`;
- `cupons` ignora esses filtros;
- comissao ausente e tratada como `0%`.
- GUI: permite selecionar varias categorias e escolher execucao com navegador visual (nao headless).

## Banco e migracoes

```bash
alembic -c db/alembic.ini upgrade head
```

Importante para ambientes ja existentes: execute a migracao antes de rodar GUI/scheduler.
Sem isso, jobs de ofertas/ofertas_relampago podem abortar por schema desatualizado
(ex.: coluna `comissao_percentual` ausente em `ml_ofertas`/`ml_ofertas_relampago`).

## Docker local

```bash
docker compose -f deploy/docker/docker-compose.local.yml up -d --build
```

## Docs

- `docs/README_REFACTOR.md`
- `docs/README_GUI.md`
- `docs/README_PIPELINE.md`
