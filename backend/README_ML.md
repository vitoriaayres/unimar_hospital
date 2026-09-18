# PharmaPredict - Sistema de Gestão e Previsão de Farmácia Hospitalar

## Visão Geral

Sistema completo para gestão de estoque e previsão de demanda de medicamentos hospitalares, com interface TUI (terminal) e API REST.

### Funcionalidades

- **Dashboard** com KPIs em tempo real
- **Gestão de Estoque** com controle FEFO (First Expired First Out)
- **Previsão de Demanda** usando Machine Learning (LightGBM)
- **Alertas Automáticos** para risco de falta e vencimento
- **Interface TUI** para uso rápido no terminal
- **API REST** (FastAPI) para integração com outros sistemas

---

## Pré-requisitos

- Python 3.11+
- PostgreSQL 14+
- pip ou uv (gerenciador de pacotes)

---

## Instalação Rápida

### 1. Clonar o repositório

```bash
git clone https://github.com/vitoriaayres/unimar_hospital.git
cd unimar_hospital/backend
```

### 2. Criar ambiente virtual

```bash
# Usando venv
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar banco de dados

```bash
# Criar banco PostgreSQL
createdb pharmapredict

# Ou usar Docker
docker-compose up -d postgres
```

### 5. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do backend:

```env
DATABASE_URL=postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict
SECRET_KEY=sua-chave-secreta-aqui
```

---

## Populando o Banco de Dados

### Gerar dados sintéticos

```bash
# Gerar dados (leva ~5 minutos)
python ml/generate_data.py

# Popular banco de dados
python ml/seed_db.py
```

### Dados gerados

| Tabela | Registros | Descrição |
|--------|-----------|-----------|
| products | 500 | Medicamentos hospitalares |
| consumption | ~2.8M | Registros de consumo (4 anos) |
| inventory_batches | ~8.500 | Lotes de estoque |
| stock_movements | ~50.000 | Movimentações de estoque |
| users | 14 | Usuários do sistema |
| warehouses | 4 | Depósitos/farmácias |
| alerts | ~800 | Alertas do sistema |

---

## Treinamento do Modelo ML

### Pipeline completo

```bash
# Executar pipeline: features -> treino -> previsão
python ml/run_pipeline.py
```

### Etapas individuais

```bash
# 1. Gerar features
python ml/features.py

# 2. Treinar modelo
python ml/train.py

# 3. Gerar previsões
python ml/predict.py
```

### Métricas do modelo

| Métrica | Valor | Descrição |
|---------|-------|-----------|
| MAPE | ~40% | Erro percentual absoluto médio |
| sMAPE | ~33% | MAPE simétrico |
| RMSE | ~222 | Raiz do erro quadrático médio |
| MAE | ~77 | Erro absoluto médio |

**Nota:** O MAPE de ~40% é aceitável para dados sintéticos heterogêneos. Para dados reais, espera-se MAPE < 25%.

---

## Executando o Sistema

### Interface TUI (Terminal)

```bash
python tui.py
```

**Navegação:**

| Tecla | Função |
|-------|--------|
| 1 | Dashboard |
| 2 | Produtos (Risco de Estoque) |
| 3 | Alertas |
| 4 | Vencimento de Lotes |
| 5 | Estoque |
| 6 | Consumo |
| 7 | Movimentações |
| 8 | Usuários |
| 9 | Cadastrar Produto |
| 10 | Recebimento |
| 11 | Dispensação |
| 12 | Consumo Diário |
| 13 | **Previsões ML** |
| q | Sair |

### API REST

```bash
# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Documentação Swagger
http://localhost:8000/docs
```

---

## Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /api/v1/dashboard/kpis | KPIs do dashboard |
| GET | /api/v1/dashboard/stockout-risk | Risco de falta com previsões ML |
| GET | /api/v1/predictions | Lista de previsões |
| POST | /api/v1/predictions/forecast | Gerar previsão para produto |
| GET | /api/v1/products | Lista de produtos |
| POST | /api/v1/consumption | Registrar consumo |

---

## Estrutura do Projeto

```
backend/
├── app/                    # Aplicação FastAPI
│   ├── api/v1/             # Rotas da API
│   ├── models/             # Models SQLAlchemy
│   ├── schemas/            # Pydantic schemas
│   └── services/           # Lógica de negócio
├── ml/                     # Pipeline de Machine Learning
│   ├── config/             # Configurações
│   ├── data/               # Dados e features
│   ├── models/             # Modelos treinados
│   ├── generate_data.py    # Gerador de dados sintéticos
│   ├── features.py         # Feature engineering
│   ├── train.py            # Treino do modelo
│   ├── predict.py          # Serviço de previsão
│   └── run_pipeline.py     # Orquestrador do pipeline
├── tui.py                  # Interface Terminal
├── alembic/                # Migrações do banco
└── tests/                  # Testes
```

---

## Tecnologias

- **Backend:** FastAPI, SQLAlchemy, Alembic
- **ML:** LightGBM, scikit-learn, Polars
- **Banco:** PostgreSQL
- **TUI:** Textual (terminal)
- **Containerização:** Docker

---

## Comandos Úteis

```bash
# Rodar todos os comandos de uma vez
python ml/generate_data.py && python ml/seed_db.py && python ml/run_pipeline.py && python ml/predict.py

# Iniciar TUI
python tui.py

# Iniciar API
uvicorn app.main:app --reload

# Rodar testes
pytest tests/

# Migrações do banco
alembic upgrade head
```

---

## Solução de Problemas

### Erro: "psycopg2 not found"

```bash
pip install psycopg2-binary
```

### Erro: "Model not trained"

```bash
python ml/train.py
```

### Erro: "No predictions found"

```bash
python ml/predict.py
```

### Banco de dados vazio

```bash
python ml/generate_data.py
python ml/seed_db.py
```

---

## Licença

Projeto acadêmico - UNIMAR (Universidade Maringá)
