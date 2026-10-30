# Roteiro: apresentação de código e documentação

Sugestão de ordem para ~15–20 minutos. Cada bloco diz **o que abrir** e **o que falar**.

## Antes de começar (5 min antes)

```powershell
docker compose up -d                       # Postgres
cd backend;  uv run uvicorn app.main:app   # API (terminal 1)
cd frontend; npm.cmd run dev               # Front (terminal 2)
```

Deixe abertos no navegador: `http://localhost:3000` (logado) e `http://localhost:8000/docs`.
No VS Code, abra o `README.md` em modo preview (`Ctrl+Shift+V`).

## 1. Problema e visão geral (2 min)

- **Abrir:** `README.md` → [docs/01-visao-geral.md](../01-visao-geral.md)
- **Falar:** falta × vencimento de medicamentos; a previsão substitui a média de consumo.

## 2. Arquitetura (3 min)

- **Abrir:** [docs/02-arquitetura.md](../02-arquitetura.md) (os diagramas renderizam no preview)
- **Falar:** front Next.js → API FastAPI → PostgreSQL; pipeline de ML roda por script e grava
  modelo + previsões; a API só lê. Mostrar a tabela de decisões.
- **Se perguntarem do planejamento:** [planejamento/LEIA-ME.md](../planejamento/LEIA-ME.md)
  mostra o que foi planejado e o que mudou (e por quê).

## 3. Backend (4 min)

- **Abrir:** `backend/app/api/v1/predictions.py`
- **Mostrar o padrão:** `router`, injeção de `db` e `current_user`, resposta com schema Pydantic.
- **Abrir:** `backend/app/models/__init__.py` (tabelas) e `backend/app/api/deps.py` (perfis).
- **Ao vivo:** `http://localhost:8000/docs` → **Authorize** → `GET /api/v1/predictions/model-report`.

## 4. Pipeline de ML (4 min)

- **Abrir:** [docs/05-pipeline-ml.md](../05-pipeline-ml.md) (diagrama do pipeline)
- **Código:** `backend/ml/features.py` (`add_lag_features`, `add_rolling_features`) e
  `backend/ml/train.py` (`train_lightgbm`, `tune_blend_weight`, `compute_metrics`).
- **Falar:** divisão temporal (sem vazamento de futuro), comparação com o método atual.

## 5. Frontend (3 min)

- **Abrir:** `frontend/src/app/model/page.tsx` e `frontend/src/hooks/usePredictions.ts`
- **Falar:** tela → hook → React Query → API. Componentes reutilizáveis em `components/ui`.
- **Ao vivo:** abrir a tela **Modelo** e a **Ler código** (câmera).

## 6. Qualidade (2 min)

- **Abrir:** [docs/07-testes-e-qualidade.md](../07-testes-e-qualidade.md)
- **Ao vivo:** `cd backend; uv run pytest`
- **Falar:** testes, cobertura, lint (ruff), CI no GitHub Actions.

## Perguntas prováveis

| Pergunta | Resposta curta |
|---|---|
| Por que dados fictícios? | Dados de hospital são sigilosos (LGPD). A simulação reproduz padrões reais e é reproduzível (seed 42). |
| Por que LightGBM? | Rápido, ótimo em dados tabulares com muitas variáveis, e mostra a importância de cada variável. |
| Como evitam "olhar o futuro"? | Treino com dados antigos, teste com o período mais recente; variáveis usam só dados passados. |
| Como se compara ao que existe? | Ver [05-pipeline-ml.md](../05-pipeline-ml.md#resultados): erro do modelo × média móvel. |
| E em produção real? | Trocar a base fictícia pelo histórico do hospital e rodar o pipeline diariamente. |
