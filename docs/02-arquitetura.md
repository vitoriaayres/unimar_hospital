# Arquitetura

## Visão de componentes

```mermaid
flowchart LR
    U[Usuário<br/>navegador] -->|HTTP :3000| FE[Frontend<br/>Next.js 14]
    U -->|câmera| BC[Leitor de código<br/>@zxing/browser]
    BC --> FE
    FE -->|REST + JWT :8000| BE[Backend<br/>FastAPI]
    BE -->|SQLAlchemy async| DB[(PostgreSQL 15)]
    BE -->|lê| ART[Artefatos do modelo<br/>ml/models + ml/data]

    subgraph Pipeline de ML  [Pipeline de ML - roda por script]
        GEN[generate_data.py<br/>base fictícia] --> RESET[full_reset.py<br/>carga no banco]
        RESET --> DB
        DB --> FEAT[features.py]
        FEAT --> TRAIN[train.py<br/>LightGBM]
        TRAIN --> ART
        TRAIN --> PRED[predict.py]
        PRED --> DB
    end
```

| Parte | Tecnologia | Pasta |
|---|---|---|
| Frontend | Next.js 14 (App Router), React 18, Tailwind, React Query, Recharts | `frontend/` |
| Backend | FastAPI, SQLAlchemy 2 async, Alembic, Pydantic 2, JWT | `backend/app/` |
| Banco | PostgreSQL 15 | `docker-compose.yml` |
| ML | Polars, LightGBM, scikit-learn, Faker | `backend/ml/` |
| Infra | Docker Compose, GitHub Actions | `docker-compose.yml`, `.github/` |

## Fluxo de uma previsão

1. `ml/run_pipeline.py` lê o consumo do banco, gera as variáveis, treina o modelo e grava:
   - `ml/models/model_production.pkl`: modelo treinado
   - `ml/data/metrics_production.json`: métricas no teste
   - `ml/data/model_report_production.json`: dados dos gráficos da tela **Modelo**
   - tabela `predictions`: previsão de cada produto
2. O backend lê esses arquivos e a tabela e serve em `/api/v1/predictions/...`.
3. O frontend exibe nas telas **Previsões**, **Modelo** e no **Dashboard**.

O modelo roda **dentro do processo do backend** (sem servidor de modelo separado): o arquivo `.pkl`
tem ~2,5 MB e a inferência leva milissegundos.

## Modelo de dados

```mermaid
erDiagram
    users ||--o{ stock_movements : registra
    users ||--o{ alerts : reconhece
    products ||--o{ inventory_batches : possui
    products ||--o{ consumption : consome
    products ||--o{ predictions : prevê
    products ||--o{ alerts : dispara
    warehouses ||--o{ inventory_batches : armazena
    inventory_batches ||--o{ stock_movements : movimenta

    products {
        uuid id
        string sku
        string barcode
        string name
        enum category
        string atc_code
        float unit_cost
        int min_stock_level
        int max_stock_level
        int lead_time_days
        bool controlled_substance
    }
    inventory_batches {
        uuid id
        string batch_number
        date expiry_date
        int quantity
        enum status
    }
    stock_movements {
        uuid id
        int quantity_change
        enum movement_type
    }
    consumption {
        uuid id
        date consumption_date
        int quantity
        enum department
        enum prescription_type
    }
    predictions {
        uuid id
        date forecast_date
        int predicted_quantity
        int confidence_lower
        int confidence_upper
        string model_version
        float wape_score
    }
    alerts {
        uuid id
        enum alert_type
        enum severity
        bool acknowledged
    }
```

Também existe `audit_logs` (quem alterou o quê, com valores antigos e novos). Definição completa:
`backend/app/models/__init__.py`. Migrações: `backend/alembic/versions/`.

## Decisões de arquitetura

| # | Decisão | Por quê |
|---|---|---|
| 1 | **Monólito FastAPI** em vez de microsserviços | Um time pequeno, um domínio só; menos infraestrutura |
| 2 | **PostgreSQL** para tudo (inclusive séries de consumo) | ~1 milhão de linhas de consumo cabem bem com índices por produto/data |
| 3 | **Base fictícia** como parte do pipeline | Dados reais de hospital são sigilosos (LGPD); a simulação é reproduzível (seed 42) |
| 4 | **Inferência no próprio backend** | Modelo pequeno; evita um serviço a mais |
| 5 | **Previsão em lote por script** em vez de fila (Celery) | Previsão diária não precisa de tempo real |
| 6 | **JWT** com access + refresh token | API sem estado, padrão do FastAPI |
| 7 | **Blend modelo + média móvel** | Reduz erro em produtos de baixo giro; peso escolhido na validação |

O planejamento inicial (com Celery, Redis, MLflow etc.) está em
[planejamento/](planejamento/LEIA-ME.md), com a comparação do que mudou.
