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

## Primeira vez em um computador novo

Os dados não vão pelo Git: sem este passo o banco fica vazio e o login não funciona. Abra o
Docker Desktop e rode a partir da pasta do projeto. Leva cerca de 35 minutos no total.

```powershell
docker compose up -d
cd backend
uv sync
uv run python ml/generate_data.py               # 1. gera a base fictícia (~20 min)
uv run python ml/full_reset.py                  # 2. APAGA o banco e carrega a base (~8 min)
uv run python ml/ajustar_estoque.py --aplicar   # 3. recalcula níveis e saldos de estoque
uv run python ml/predict.py                     # 4. gera as previsões com o modelo salvo (~2 min)
uv run python ml/ajustar_estoque.py --alertas   # 5. refaz os alertas de falta
cd ../frontend
npm.cmd install
```

Siga essa ordem, sem pular etapas. Em máquinas com pouca memória (8 GB), feche outros programas
antes do passo 1. Depois disso, use sempre a seção abaixo.

## Rodar no dia a dia (Windows)

Abra o Docker Desktop e use dois terminais, ambos na pasta do projeto.

```powershell
# Terminal 1: banco e backend (http://localhost:8000/docs)
docker compose up -d
cd backend
uv run uvicorn app.main:app --reload
```

```powershell
# Terminal 2: frontend (http://localhost:3000)
cd frontend
npm.cmd run dev
```

Login: `admin@hospital.gov.br` / `admin123`

Os dados ficam salvos no volume do Docker, então os passos da primeira vez não se repetem.

## Cuidados

- **Não rode `ml/full_reset.py` nem `docker compose down -v` sem necessidade:** os dois apagam
  o banco. Depois de qualquer um deles, refaça os passos 2 a 5 da primeira vez.
- **Não rode `criar_admin.py`:** o `full_reset.py` já cria o admin, e esse script usa outra senha.
- **Escolha um modo só:** o modo de desenvolvimento e o Docker completo usam as mesmas portas
  (8000 e 3000). Pare um antes de subir o outro.

## Rodar tudo no Docker

Alternativa ao dia a dia. O banco precisa já ter os dados da primeira vez.

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

## Retreinar o modelo

Só é necessário para mudar o modelo, não para rodar o sistema. Tudo roda a partir de `backend/`,
com o Postgres no ar. Detalhes em [docs/05-pipeline-ml.md](docs/05-pipeline-ml.md).

```powershell
uv run python ml/run_pipeline.py                # 1. features -> treino -> previsões (~3 min)
uv run python ml/ajustar_estoque.py --alertas   # 2. refaz os alertas de falta
uv run python ml/report.py                      # 3. gráficos do modelo em docs/imagens/
```

O resultado aparece na tela **Modelo** (`/model`) do sistema. O treino altera o modelo e as
métricas versionados no Git e cria cópias com data em `ml/models/` e `ml/data/`, que não precisam
ser commitadas.

Atalhos que não treinam de novo:

```powershell
uv run python ml/predict.py        # refaz as previsões dos 7 dias com o modelo atual
uv run python ml/build_report.py   # refaz o relatório da tela Modelo a partir do modelo salvo
uv run python ml/barcodes.py       # dá códigos de barras EAN-13 fictícios aos produtos sem código
```

## Testes

```powershell
# A partir da pasta do projeto, um comando por terminal
cd backend;  uv run pytest
cd frontend; npm.cmd test
```
