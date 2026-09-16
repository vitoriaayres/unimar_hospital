# PharmaPredict 🏥💊

> Sistema Inteligente de Previsão de Demanda para Farmácia Hospitalar

PharmaPredict é um sistema completo de gestão de estoque farmacêutico hospitalar com **IA ativa** para previsão de demanda, alertas de risco de desabastecimento e dashboards intuitivos. Desenvolvido como projeto acadêmico para resolver problemas reais de farmácias hospitalares.

## ✨ Funcionalidades Principais

| Módulo | Descrição |
|--------|-----------|
| **📦 Gestão de Estoque** | Controle de lotes, validades (FEFO), movimentos, rastreabilidade completa |
| **📊 Consumo Histórico** | Registro e análise de consumo por departamento, tipo de prescrição, sazonalidade |
| **🔮 Previsão de Demanda (IA)** | Modelos ML (LightGBM, XGBoost, LSTM) com intervalos de confiança |
| **🚨 Alertas Inteligentes** | Risco de falta, vencimento próximo, excesso de estoque - com antecedência de 7+ dias |
| **📈 Dashboards Executivos** | KPIs em tempo real, heatmaps de risco, timeline de vencimentos, tendências |
| **📄 Relatórios Automatizados** | PDF/Excel agendados: posição de estoque, previsões, alertas, auditoria |
| **👥 Gestão de Usuários** | RBAC (Farmacêutico, Gerente, Admin), JWT + Refresh Tokens, Auditoria completa |

## 🏗️ Arquitetura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js 14    │────▶│   FastAPI       │────▶│  PostgreSQL 15  │
│   (Frontend)    │     │   (Backend)     │     │  + Partitioning │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  Redis   │ │  Celery  │ │  MLflow  │
              │ (Cache/  │ │ (Async   │ │ (ML      │
              │  Broker) │ │  Tasks)  │ │ Registry)│
              └──────────┘ └──────────┘ └──────────┘
```

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI 0.110+** - API assíncrona, validação Pydantic, OpenAPI automático
- **SQLAlchemy 2.0 + Alembic** - ORM assíncrono, migrações versionadas
- **PostgreSQL 15** - Particionamento nativo para séries temporais
- **LightGBM / XGBoost / PyTorch** - Modelos de previsão
- **MLflow** - Experiment tracking, model registry, versionamento
- **Celery + Redis** - Processamento assíncrono (treino, predições, relatórios)
- **JWT + bcrypt** - Autenticação stateless segura

### Frontend
- **Next.js 14 (App Router)** - React Server Components, Streaming SSR
- **TypeScript 5** - Type safety end-to-end
- **Tailwind CSS + shadcn/ui** - Design system acessível e responsivo
- **Recharts** - Gráficos interativos e performáticos
- **TanStack Table** - Tabelas avançadas com ordenação, filtro, paginação
- **React Hook Form + Zod** - Formulários validados
- **Zustand** - Estado global leve

### DevOps & Qualidade
- **Docker + Docker Compose** - Ambientes dev/prod consistentes
- **GitHub Actions** - CI/CD completo (lint, typecheck, test, build, security)
- **Ruff + MyPy** - Linting e typechecking rápidos
- **pytest + Vitest + Playwright** - Pirâmide de testes completa
- **Prometheus + Grafana + Loki + Tempo** - Observabilidade full-stack

## 🚀 Início Rápido

### Pré-requisitos
- Docker Desktop 4.25+
- Git
- (Opcional) uv para desenvolvimento backend local

### 1. Clone e suba o ambiente
```bash
git clone <repo-url>
cd PharmaPredict

# Sobe todos os serviços (Postgres, Redis, MLflow, MinIO, Prometheus, Grafana)
docker compose up -d

# Verifica saúde dos serviços
docker compose ps
```

### 2. Backend
```bash
cd backend

# Instala dependências (usa uv - rápido!)
uv sync

# Roda migrações
uv run alembic upgrade head

# Gera dados sintéticos (3 anos, 500 SKUs)
uv run python -m ml.generate_data

# Treina modelo baseline
uv run python -m ml.train --model lightgbm --trials 20

# Inicia API
uv run uvicorn app.main:app --reload
# API: http://localhost:8000/docs
```

### 3. Frontend
```bash
cd frontend

# Instala dependências
npm install

# Inicia em modo desenvolvimento
npm run dev
# App: http://localhost:3000
```

### 4. Acesse os serviços
| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | admin@hospital.gov.br / admin123 |
| **Backend API** | http://localhost:8000/docs | - |
| **MLflow** | http://localhost:5001 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |

## 📁 Estrutura do Projeto

```
PharmaPredict/
├── SPEC.md                 # Especificação técnica completa
├── ARCHITECTURE.md         # Arquitetura, ADRs, diagramas
├── ML_PIPELINE.md          # Pipeline de ML detalhado
├── PROJECT_PLAN.md         # Plano de 10 semanas, 7 pessoas
├── docker-compose.yml      # Stack completo de desenvolvimento
├── .github/workflows/      # CI/CD pipelines
│
├── backend/                # FastAPI Application
│   ├── app/
│   │   ├── api/v1/         # Rotas da API (auth, products, inventory, predictions, dashboard, alerts)
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas (contratos da API)
│   │   ├── services/       # Lógica de negócio
│   │   ├── ml/             # Pipeline ML (data gen, features, train, evaluate, predict, registry)
│   │   ├── tasks/          # Celery tasks
│   │   └── utils/          # Utilitários (security, logging, exceptions)
│   ├── alembic/            # Migrações de banco
│   ├── tests/              # Testes unitários e integração
│   ├── pyproject.toml      # Dependências (uv)
│   └── Dockerfile
│
├── frontend/               # Next.js 14 Application
│   ├── src/
│   │   ├── app/            # App Router pages (dashboard, products, inventory, predictions, alerts, reports)
│   │   ├── components/     # UI components (ui/, charts/, forms/, tables/, layout/)
│   │   ├── lib/            # API client, auth, utils
│   │   ├── hooks/          # Custom React hooks
│   │   ├── stores/         # Zustand stores
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── Dockerfile
│
└── ml/                     # ML Pipeline (standalone)
    ├── config/             # YAML configs (data_generation.yaml)
    ├── data/               # Dados sintéticos gerados (Parquet)
    └── generate_data.py    # Gerador principal
```

## 🧪 Testes

```bash
# Backend
cd backend
uv run pytest                    # Todos os testes
uv run pytest -m unit            # Apenas unitários
uv run pytest -m integration     # Apenas integração
uv run pytest --cov=app          # Com coverage

# Frontend
cd frontend
npm run test                     # Unitários (Vitest)
npm run test:e2e                 # E2E (Playwright)
npm run test:ui                  # UI do Vitest
```

## 📊 Pipeline de ML

```bash
# Gera dados sintéticos realistas
uv run python -m ml.generate_data

# Treina modelos com Optuna HPO
uv run python -m ml.train --model lightgbm --trials 50
uv run python -m ml.train --model xgboost --trials 50
uv run python -m ml.train --model lstm --epochs 100

# Avalia e compara
uv run python -m ml.evaluate --run-id <run_id>

# Promove para produção
uv run python -m ml.registry promote --model-version <version>
```

### Métricas Alvo
| Métrica | Target |
|---------|--------|
| MAPE (30 dias) | < 15% |
| sMAPE | < 15% |
| Precision@7d (shortage) | > 80% |
| Recall@7d (shortage) | > 70% |
| Cobertura IC 80% | 75-85% |

## 🔧 Configuração

### Variáveis de Ambiente
Copie `.env.example` para `.env` e ajuste:

```bash
cp .env.example .env
# Edite SECRET_KEY, passwords, etc.
```

### Principais Configurações
- `ENVIRONMENT=development|staging|production`
- `SECRET_KEY` - **Obrigatório em produção** (mín. 32 chars)
- `POSTGRES_*` - Conexão com banco
- `MLFLOW_*` - Tracking de experimentos
- `CORS_ORIGINS` - Origens permitidas no frontend

## 📈 Monitoramento

### Métricas Disponíveis (Prometheus)
- `http_requests_total` - Requests por endpoint/status
- `http_request_duration_seconds` - Latência por endpoint
- `ml_training_duration_seconds` - Tempo de treino
- `ml_prediction_latency_seconds` - Latência de inferência
- `celery_task_duration_seconds` - Tempo de tasks assíncronas

### Dashboards Grafana
- **System Overview** - CPU, RAM, Disk, Network
- **API Performance** - Latência, throughput, erros
- **ML Pipeline** - Treino, métricas, drift detection
- **Business KPIs** - Estoque, alertas, previsões

## 🔒 Segurança

- ✅ Autenticação JWT stateless com refresh tokens HttpOnly
- ✅ Senhas com bcrypt (12 rounds)
- ✅ RBAC (3 roles: pharmacist, manager, admin)
- ✅ Auditoria imutável de todas as mutações de estoque
- ✅ Rate limiting (via NGINX/Edge)
- ✅ Headers de segurança (CSP, HSTS, X-Frame-Options)
- ✅ Validação rigorosa de entrada (Pydantic/Zod)
- ✅ Scan de vulnerabilidades (Trivy no CI)

## 📝 Documentação

| Documento | Descrição |
|-----------|-----------|
| [SPEC.md](SPEC.md) | Especificação técnica completa |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Arquitetura, ADRs, diagramas Mermaid |
| [ML_PIPELINE.md](ML_PIPELINE.md) | Pipeline de ML end-to-end |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | Plano de execução 10 semanas |
| [API Docs](http://localhost:8000/docs) | Swagger UI (em execução) |

## 🤝 Contribuição

1. Fork o projeto
2. Crie branch: `git checkout -b feat/nova-funcionalidade`
3. Commit: `git commit -m 'feat: adiciona nova funcionalidade'`
4. Push: `git push origin feat/nova-funcionalidade`
5. Abra Pull Request

### Padrões de Commit (Conventional Commits)
- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `refactor:` Refatoração sem mudança de comportamento
- `docs:` Documentação
- `test:` Testes
- `chore:` Manutenção

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

## 👥 Equipe

Desenvolvido por 7 estudantes em 10 semanas como projeto acadêmico universitário.

## 🙏 Agradecimentos

- Literatura de farmácia hospitalar brasileira (ANVISA, SUS)
- Comunidade open source (FastAPI, Next.js, LightGBM, MLflow, etc.)
- Hospital parceiro para validação de requisitos

---

**PharmaPredict** - Transformando dados em decisões para salvar vidas 💙