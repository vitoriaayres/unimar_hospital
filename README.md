# PharmaPredict

**Gestão de estoque da farmácia hospitalar com previsão de demanda de medicamentos.**
Projeto do Hospital Beneficente Unimar.

O sistema prevê o consumo dos próximos 7 dias de cada medicamento com um modelo LightGBM, alerta
sobre risco de falta e lotes perto do vencimento e permite localizar produtos pelo código de barras.

## Documentação

| # | Documento | Conteúdo |
|---|---|---|
| 1 | [Visão geral](docs/01-visao-geral.md) | Problema, solução, telas, perfis |
| 2 | [Arquitetura](docs/02-arquitetura.md) | Componentes, fluxo, modelo de dados, decisões |
| 3 | [Backend (API)](docs/03-backend-api.md) | Organização do código e todas as rotas |
| 4 | [Frontend](docs/04-frontend.md) | Estrutura, padrão das telas, identidade visual |
| 5 | [Pipeline de ML](docs/05-pipeline-ml.md) | Base fictícia, variáveis, treino, **resultados** |
| 6 | [Leitor de código de barras](docs/06-leitor-codigo-barras.md) | Câmera e busca por código |
| 7 | [Testes e qualidade](docs/07-testes-e-qualidade.md) | Testes, cobertura, lint, CI |
| — | [Planejamento original](docs/planejamento/LEIA-ME.md) | Especificação inicial e o que mudou |
| — | [Roteiros de apresentação](docs/apresentacao/) | Passo a passo das demos |

## Stack

| Parte | Tecnologia | Pasta |
|---|---|---|
| Frontend | Next.js 14, React 18, Tailwind, React Query, Recharts | `frontend/` |
| Backend | FastAPI, SQLAlchemy async, Alembic, JWT | `backend/app/` |
| Banco | PostgreSQL 15 (Docker) | `docker-compose.yml` |
| ML | Polars, LightGBM, scikit-learn, Faker | `backend/ml/` |

## Pré-requisitos

- Docker Desktop
- [uv](https://docs.astral.sh/uv/) (Python 3.11+)
- Node.js 20+

## Rodar em desenvolvimento (Windows)

```powershell
# 1. Banco (só o Postgres)
docker compose up -d

# 2. Backend: http://localhost:8000/docs
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# 3. Frontend (outro terminal): http://localhost:3000
cd frontend
npm.cmd install
npm.cmd run dev
```

Login: `admin@hospital.gov.br` / `admin123`

## Rodar tudo no Docker

```powershell
# Builda uma imagem por vez (as duas juntas travam máquina com pouca RAM)
docker compose --profile full build backend
docker compose --profile full build frontend
docker compose --profile full up -d
```

Sobe Postgres, backend (aplica as migrações ao iniciar) e frontend. O backend lê o modelo e as
previsões de `backend/ml/models` e `backend/ml/data`, montados como volume.

A memória do Docker é limitada em `%UserProfile%\.wslconfig` (`memory=3GB`, `processors=4`).
Depois de alterar esse arquivo, rode `wsl --shutdown` e reabra o Docker Desktop.

## Base fictícia e treino do modelo

Tudo roda a partir de `backend/`, com o Postgres no ar. Detalhes em
[docs/05-pipeline-ml.md](docs/05-pipeline-ml.md).

```powershell
uv run python ml/generate_data.py   # 1. gera a base fictícia (ml/config/data_generation.yaml)
uv run python ml/full_reset.py      # 2. APAGA o banco e carrega a base fictícia
uv run python ml/run_pipeline.py    # 3. features -> treino -> previsões
uv run python ml/report.py          # 4. gráficos do modelo em docs/imagens/
```

O resultado aparece na tela **Modelo** (`/model`) do sistema.

Atalhos que não treinam de novo (leves, servem depois de um `full_reset.py`):

```powershell
uv run python ml/predict.py        # refaz as previsões dos 7 dias com o modelo atual
uv run python ml/build_report.py   # refaz o relatório da tela Modelo a partir do modelo salvo
uv run python ml/barcodes.py       # dá códigos de barras EAN-13 fictícios aos produtos sem código
```

## Testes

```powershell
cd backend;  uv run pytest
cd frontend; npm.cmd test
```
