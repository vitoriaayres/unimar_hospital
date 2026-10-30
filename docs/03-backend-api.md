# Backend (API)

FastAPI em `backend/app/`. Documentação interativa (Swagger) em **http://localhost:8000/docs**
com o backend no ar. Todas as rotas abaixo têm o prefixo `/api/v1` e, exceto login e refresh,
exigem o cabeçalho `Authorization: Bearer <token>`.

## Organização do código

```
backend/app/
├── main.py            # cria o app, CORS, /health, registra os routers
├── config.py          # configurações (variáveis de ambiente, .env)
├── database.py        # engine e sessão SQLAlchemy async
├── models/__init__.py # tabelas (SQLAlchemy ORM)
├── schemas/           # contratos de entrada/saída (Pydantic)
├── api/deps.py        # dependências: sessão do banco, usuário logado, perfis
└── api/v1/            # um arquivo por recurso
```

Cada arquivo em `api/v1/` segue o mesmo padrão: `router = APIRouter(prefix=...)`, rotas recebem
`db` e `current_user` por injeção de dependência e respondem com um schema Pydantic.

## Rotas

### Autenticação (`auth.py`)
| Método | Rota | Descrição |
|---|---|---|
| POST | `/login` | Login (form `username`/`password`) → access + refresh token |
| POST | `/refresh` | Novo access token |
| POST | `/logout` | Encerra a sessão |
| GET | `/me` | Usuário logado |
| PATCH | `/me/password` | Troca de senha |
| POST | `/register` | Cria usuário (admin) |
| GET | `/users` | Lista usuários (admin) |
| PATCH | `/users/{id}` | Edita usuário (admin) |

### Produtos (`products.py`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/products` | Lista com paginação e filtros |
| POST | `/products` | Cria (manager/admin) |
| GET | `/products/by-barcode/{barcode}` | Busca por código de barras |
| GET | `/products/{id}` | Detalhe |
| PATCH | `/products/{id}` | Edita (manager/admin) |
| DELETE | `/products/{id}` | Exclusão lógica (admin) |

### Estoque (`inventory.py`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/inventory/summary` | Resumo de estoque por produto |
| GET | `/inventory/batches` | Lotes por validade (paginado); filtros `search`, `product_id`, `status`, `expiring_within_days`, `in_stock` |
| POST | `/inventory/batches` | Novo lote (manager/admin) |
| GET | `/inventory/batches/{id}` | Detalhe do lote |
| PATCH | `/inventory/batches/{id}` | Edita lote (manager/admin) |
| POST | `/inventory/movements` | Registra movimentação |
| GET | `/inventory/movements` | Lista movimentações; filtros `product_id`, `batch_id`, `movement_type` |

### Consumo (`consumption.py`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/consumption` | Lista registros |
| POST | `/consumption` | Registra consumo |
| POST | `/consumption/bulk` | Registra vários |
| POST | `/consumption/import` | Importa CSV |

### Previsões e modelo (`predictions.py`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/predictions` | Previsões de 7 dias gravadas pelo pipeline; busca `search` e ordenação `sort_by` |
| POST | `/predictions/forecast` | Previsão diária de um produto (até 90 dias) a partir da previsão de 7 dias |
| GET | `/predictions/model-report` | Avaliação do modelo (tela **Modelo**) |
| GET | `/predictions/models` | Modelo em produção e métricas |

### Dashboard (`dashboard.py`) e Alertas (`alerts.py`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/dashboard` | Tudo do dashboard em uma chamada |
| GET | `/dashboard/kpis` | Indicadores |
| GET | `/dashboard/stockout-risk` | Produtos com menor cobertura (estoque ÷ previsão) |
| GET | `/dashboard/expiry-timeline` | Lotes com saldo que vencem em breve |
| GET | `/dashboard/consumption-trends` | Consumo diário por setor e categoria; filtro `product_id` |
| GET | `/alerts` | Alertas (paginado) |
| POST | `/alerts/{id}/acknowledge` | Reconhece alerta |
| POST | `/alerts/bulk-acknowledge` | Reconhece vários |
| GET | `/alerts/rules` | Regras de alerta |
| PATCH | `/alerts/rules/{id}` | Liga/desliga uma regra (manager/admin; fica em memória até reiniciar) |

## Segurança

- Senhas com **bcrypt** (`passlib`).
- **JWT** assinado: access token de 15 minutos + refresh token de 7 dias.
- Perfis verificados no backend (`pharmacist`, `manager`, `admin`), não só escondidos no front.
- CORS restrito à origem do frontend.

## Banco e migrações

```powershell
cd backend
uv run alembic upgrade head          # aplica migrações
uv run alembic revision -m "..."     # nova migração
```
