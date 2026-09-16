# Spec: PharmaPredict - Hospital Pharmacy Demand Prediction System

## Objective

Build an AI-powered hospital pharmacy management system that goes beyond basic inventory tracking to provide **active demand forecasting** and **shortage risk alerts**. The system serves pharmacists and pharmacy managers at a single hospital pharmacy, enabling proactive inventory decisions through intuitive dashboards and AI-driven insights.

**Target Users:**
- Farmacêuticos hospitalares (daily operations, dispensing, restocking)
- Gerentes de farmácia (planning, budgeting, supplier negotiations)
- Administradores hospitalares (oversight, compliance reporting)

**Success Criteria:**
- Dashboard loads in < 2s with real-time inventory + predictions
- Demand forecasts achieve MAPE < 15% on synthetic test data
- Shortage alerts trigger ≥ 7 days before stockout with > 80% precision
- System supports 500+ SKUs with sub-second query response
- All 7 team members can work in parallel with minimal merge conflicts

---

## Tech Stack

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Backend API** | FastAPI | 0.110+ | Async, native Pydantic, excellent ML integration, OpenAPI auto-docs |
| **Frontend** | Next.js | 14+ (App Router) | RSC, streaming, excellent dashboard UX, Vercel deploy |
| **Database** | PostgreSQL | 15+ | ACID, JSONB for flexible ML metadata, mature |
| **ORM** | SQLAlchemy | 2.0+ | Async support, type-safe, migration via Alembic |
| **ML Framework** | scikit-learn, XGBoost, LightGBM | Latest | Proven tabular forecasting, fast training |
| **Deep Learning (optional)** | PyTorch / TensorFlow | Latest | LSTM/Transformer for advanced models |
| **Experiment Tracking** | MLflow | 2.10+ | Model versioning, metrics comparison |
| **Task Queue** | Celery + Redis | Latest | Async ML training, report generation |
| **Auth** | JWT (python-jose) + bcrypt | Standard | Stateless, scalable, secure |
| **Charts** | Recharts / Tremor | Latest | React-native, accessible, performant |
| **UI Components** | shadcn/ui + Tailwind CSS | Latest | Accessible, customizable, fast dev |
| **Testing** | pytest (backend), Vitest + Playwright (frontend) | Latest | Comprehensive coverage |
| **Containerization** | Docker + Docker Compose | Latest | Consistent dev/prod environments |
| **CI/CD** | GitHub Actions | - | Automated test, lint, build |

---

## Commands

```bash
# Development
docker compose up -d                    # Start all services (Postgres, Redis, MLflow)
cd backend && uv run uvicorn app.main:app --reload  # Backend dev server
cd frontend && npm run dev              # Frontend dev server (port 3000)

# Database
cd backend && uv run alembic upgrade head        # Run migrations
cd backend && uv run alembic revision --autogenerate -m "msg"  # New migration

# ML Pipeline
cd backend && uv run python -m ml.generate_synthetic_data  # Generate fake data
cd backend && uv run python -m ml.train --model xgboost    # Train model
cd backend && uv run python -m ml.evaluate --run-id <id>   # Evaluate model
cd backend && uv run mlflow ui --port 5001               # MLflow UI

# Testing
cd backend && uv run pytest --cov=app --cov-report=term-missing
cd frontend && npm run test                # Vitest unit tests
cd frontend && npm run test:e2e            # Playwright E2E tests

# Quality
cd backend && uv run ruff check . && uv run ruff format .
cd backend && uv run mypy .
cd frontend && npm run lint && npm run typecheck

# Build
cd frontend && npm run build               # Production build
docker compose -f docker-compose.prod.yml build  # Production images
```

---

## Project Structure

```
PharmaPredict/
├── SPEC.md                          # This specification
├── ARCHITECTURE.md                  # Architecture decisions (ADRs)
├── docker-compose.yml               # Local dev stack
├── docker-compose.prod.yml          # Production stack
├── .github/workflows/               # CI/CD pipelines
│
├── backend/                         # FastAPI application
│   ├── pyproject.toml              # Dependencies (uv)
│   ├── uv.lock
│   ├── alembic/                    # DB migrations
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app factory
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   ├── database.py             # Async engine, session
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── inventory.py
│   │   │   ├── consumption.py
│   │   │   ├── prediction.py
│   │   │   └── alert.py
│   │   ├── schemas/                # Pydantic schemas (API contracts)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── product.py
│   │   │   ├── inventory.py
│   │   │   ├── prediction.py
│   │   │   └── dashboard.py
│   │   ├── api/                    # API routes (versioned)
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── products.py
│   │   │   │   ├── inventory.py
│   │   │   │   ├── predictions.py
│   │   │   │   ├── dashboard.py
│   │   │   │   └── alerts.py
│   │   │   └── deps.py             # Dependencies (DB, auth, etc.)
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── inventory_service.py
│   │   │   ├── prediction_service.py
│   │   │   ├── alert_service.py
│   │   │   └── dashboard_service.py
│   │   ├── ml/                     # ML Pipeline (separated for clarity)
│   │   │   ├── __init__.py
│   │   │   ├── generate_data.py    # Synthetic data generator
│   │   │   ├── features.py         # Feature engineering
│   │   │   ├── models/             # Model definitions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── baseline.py     # Moving average, exponential smoothing
│   │   │   │   ├── tree_based.py   # XGBoost, LightGBM, RF
│   │   │   │   └── deep_learning.py # LSTM, Transformer (optional)
│   │   │   ├── train.py            # Training orchestration
│   │   │   ├── evaluate.py         # Evaluation & comparison
│   │   │   ├── predict.py          # Inference service
│   │   │   ├── registry.py         # MLflow model registry
│   │   │   └── scheduler.py        # Periodic retraining
│   │   ├── tasks/                  # Celery tasks
│   │   │   ├── __init__.py
│   │   │   ├── ml_tasks.py
│   │   │   └── report_tasks.py
│   │   └── utils/                  # Shared utilities
│   │       ├── __init__.py
│   │       ├── security.py
│   │       ├── pagination.py
│   │       └── exceptions.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── unit/
│       ├── integration/
│       └── fixtures/
│
├── frontend/                        # Next.js 14+ App Router
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── .eslintrc.json
│   ├── public/
│   ├── src/
│   │   ├── app/                    # App Router pages
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Dashboard (home)
│   │   │   ├── login/page.tsx
│   │   │   ├── products/
│   │   │   │   ├── page.tsx        # List + search
│   │   │   │   └── [id]/page.tsx   # Detail + predictions
│   │   │   ├── inventory/page.tsx  # Stock levels, expiries
│   │   │   ├── predictions/page.tsx # Forecast visualization
│   │   │   ├── alerts/page.tsx     # Shortage risk alerts
│   │   │   ├── reports/page.tsx    # PDF/Excel exports
│   │   │   └── settings/page.tsx   # User preferences
│   │   ├── components/             # Shared UI components
│   │   │   ├── ui/                 # shadcn/ui primitives
│   │   │   ├── charts/             # Recharts wrappers
│   │   │   ├── forms/              # React Hook Form + Zod
│   │   │   ├── tables/             # TanStack Table wrappers
│   │   │   └── layout/             # Sidebar, Header, Breadcrumbs
│   │   ├── lib/                    # Utilities
│   │   │   ├── api.ts              # API client (fetch wrapper)
│   │   │   ├── auth.ts             # Client-side auth helpers
│   │   │   ├── utils.ts            # cn(), formatters, etc.
│   │   │   └── validations/        # Zod schemas
│   │   ├── hooks/                  # Custom React hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── usePredictions.ts
│   │   │   ├── useInventory.ts
│   │   │   └── useAlerts.ts
│   │   ├── stores/                 # Zustand/React Context state
│   │   │   ├── authStore.ts
│   │   │   └── uiStore.ts
│   │   └── types/                  # TypeScript types (synced from backend)
│   │       ├── api.ts
│   │       └── domain.ts
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── ml-pipeline/                     # Standalone ML experimentation (optional)
│   ├── notebooks/                   # Jupyter notebooks for exploration
│   ├── data/                        # Synthetic data samples
│   └── experiments/                 # Archived experiment configs
│
└── docs/
    ├── api.md                       # API documentation (auto-generated)
    ├── deployment.md
    ├── ml-model-card.md             # Model documentation
    └── user-guide.md
```

---

## Code Style

**Backend (Python):**
```python
# app/services/prediction_service.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.models.prediction import Prediction
from app.schemas.prediction import PredictionCreate, PredictionResponse
from app.database import AsyncSession


@dataclass(slots=True)
class PredictionService:
    session: AsyncSession

    async def create_predictions(
        self, product_id: UUID, horizon_days: int = 30
    ) -> list[PredictionResponse]:
        """Generate demand forecast for a product."""
        forecasts = await self._run_forecast_model(product_id, horizon_days)
        predictions = [
            Prediction(
                product_id=product_id,
                forecast_date=forecast.date,
                predicted_quantity=forecast.quantity,
                confidence_lower=forecast.lower,
                confidence_upper=forecast.upper,
                model_version=self._current_model_version,
            )
            for forecast in forecasts
        ]
        self.session.add_all(predictions)
        await self.session.flush()
        return [PredictionResponse.model_validate(p) for p in predictions]
```

**Key Conventions:**
- `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants
- Type hints mandatory; `from __future__ import annotations` at top
- `dataclass(slots=True)` for service classes; Pydantic for API schemas
- Async/await throughout; no blocking I/O in API routes
- Structured logging with `structlog` (JSON in prod, pretty in dev)
- Custom exceptions in `app/utils/exceptions.py` with error codes

**Frontend (TypeScript/React):**
```tsx
// src/components/charts/ForecastChart.tsx
'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ForecastPoint } from '@/types/api';

interface ForecastChartProps {
  data: ForecastPoint[];
  productName: string;
  horizonDays: number;
}

export function ForecastChart({ data, productName, horizonDays }: ForecastChartProps) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
        <XAxis dataKey="date" tickFormatter={(v) => new Date(v).toLocaleDateString('pt-BR')} />
        <YAxis />
        <Tooltip
          formatter={(value: number) => [value.toLocaleString('pt-BR'), 'unidades']}
          labelFormatter={(v) => new Date(v).toLocaleDateString('pt-BR')}
        />
        <Line
          type="monotone"
          dataKey="predicted_quantity"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          dot={false}
          name="Previsão"
        />
        <Line
          type="monotone"
          dataKey="confidence_upper"
          stroke="hsl(var(--primary))"
          strokeOpacity={0.2}
          strokeWidth={1}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="confidence_lower"
          stroke="hsl(var(--primary))"
          strokeOpacity={0.2}
          strokeWidth={1}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

**Key Conventions:**
- `'use client'` only where needed (interactivity, browser APIs)
- Server Components by default; Client Components for charts, forms, state
- Zod schemas for validation (shared with backend via codegen if needed)
- Tailwind utility classes; `cn()` helper for conditional classes
- Component composition over props drilling; React Context for global UI state
- Accessible by default: semantic HTML, ARIA labels, keyboard navigation

---

## Testing Strategy

| Level | Framework | Scope | Coverage Target |
|-------|-----------|-------|-----------------|
| **Unit (Backend)** | pytest + pytest-asyncio | Services, utilities, ML features | ≥ 85% |
| **Unit (Frontend)** | Vitest + React Testing Library | Components, hooks, utils | ≥ 80% |
| **Integration (Backend)** | pytest + httpx + testcontainers | API routes, DB operations, auth | ≥ 70% |
| **Integration (Frontend)** | Playwright | Critical user flows (login, dashboard, alerts) | 10+ key flows |
| **Contract** | Schemathesis / Pact | API schema compliance | All endpoints |
| **ML Model** | Custom pytest | Backtesting, drift detection, metric thresholds | MAPE < 15%, Precision > 80% |

**Test Organization:**
- `tests/unit/` — Fast, isolated, no external deps (mock DB, ML models)
- `tests/integration/` — Real DB (testcontainers), real Redis, real API calls
- `tests/e2e/` — Playwright against running dev stack
- Fixtures in `tests/fixtures/` — factories for User, Product, Inventory, Consumption

---

## Boundaries

### Always Do
- Run `pytest` and `npm run test` before every commit
- Follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`)
- Validate all API inputs with Pydantic/Zod schemas
- Use parameterized queries (SQLAlchemy ORM) — no raw SQL
- Log structured JSON with correlation IDs for tracing
- Write ADRs for architectural decisions (see `ARCHITECTURE.md`)
- Update SPEC.md when scope or requirements change

### Ask First
- Database schema changes (migrations affect all)
- Adding new external dependencies (PyPI/npm)
- Changing CI/CD pipeline configuration
- Modifying ML model registry or deployment strategy
- Exposing new API endpoints without versioning

### Never Do
- Commit secrets, API keys, or `.env` files
- Edit `uv.lock` / `package-lock.json` manually
- Disable linting/typechecking to "make it pass"
- Remove failing tests without root-cause analysis
- Store PHI/PII without encryption at rest
- Deploy to production without passing full CI pipeline

---

## Success Criteria (Measurable)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Dashboard initial load (LCP) | < 2.5s | Lighthouse CI / Playwright |
| API P95 latency (dashboard queries) | < 300ms | Prometheus/Grafana or local profiling |
| Demand forecast MAPE (30-day horizon) | < 15% | Backtest on synthetic holdout |
| Shortage alert precision (7-day lead) | > 80% | Precision@k on simulated stockouts |
| Shortage alert recall (7-day lead) | > 70% | Recall@k on simulated stockouts |
| Model retraining frequency | Weekly | Automated via Celery Beat |
| Synthetic data realism (statistical tests) | p > 0.05 | KS-test vs. real distributions (lit review) |
| Test coverage (backend) | ≥ 85% | pytest-cov |
| Test coverage (frontend) | ≥ 80% | Vitest coverage |
| Accessibility (axe-core) | 0 violations | Playwright + axe |

---

## Open Questions

1. **Authentication provider:** Hospital SSO (SAML/OIDC) or local accounts only? → *Assume local JWT for MVP, document SSO extension point.*
2. **Real-time updates:** WebSocket for live stock changes or polling sufficient? → *Start with 30s polling; WebSocket as stretch.*
3. **Supplier integration:** API for purchase orders or manual entry? → *Manual entry for MVP; document webhook endpoint for future.*
4. **Regulatory compliance:** ANVISA audit trail requirements? → *Implement immutable audit log on all inventory mutations.*
5. **Mobile/responsive:** Tablet-optimized for pharmacy floor use? → *Yes, responsive breakpoints at 768px/1024px.*
6. **Offline capability:** Service worker for intermittent connectivity? → *Defer to Phase 2; document in ADR.*
7. **Multi-language:** Portuguese only or English for internationalization? → *Portuguese primary; i18n structure ready.*

---

## Capability Map (Phase 0 Check)

This project bundles several independently testable capabilities. Per spec-driven-development, we define a capability map first:

| Module ID | Responsibility | Depends On |
|-----------|----------------|------------|
| `auth` | User authentication, roles, sessions | — |
| `catalog` | Product master data (medicaments, supplies, categories) | `auth` |
| `inventory` | Stock levels, batches, expiry tracking, movements | `catalog`, `auth` |
| `consumption` | Historical consumption recording, import/export | `catalog`, `inventory` |
| `forecasting` | ML pipeline: data prep, training, evaluation, registry | `consumption` |
| `predictions` | Serving forecasts, confidence intervals, model versioning | `forecasting`, `catalog` |
| `alerts` | Shortage risk detection, notification rules, escalation | `predictions`, `inventory` |
| `dashboard` | Aggregated views, KPIs, charts, reports | `inventory`, `predictions`, `alerts` |
| `reports` | PDF/Excel export, scheduled delivery | `dashboard`, `auth` |

**Build Order:** `auth` → `catalog` → `inventory` → `consumption` → `forecasting` → `predictions` → `alerts` → `dashboard` → `reports`

**Parallelizable Groups:**
- Group 1 (Week 1-2): `auth`, `catalog` (2 people each)
- Group 2 (Week 2-4): `inventory`, `consumption` (2 people each)
- Group 3 (Week 3-6): `forecasting` (2 people), `dashboard` UI skeleton (1 person)
- Group 4 (Week 5-8): `predictions`, `alerts` (2 people), `dashboard` integration (2 people)
- Group 5 (Week 8-10): `reports`, polish, testing, docs (all 7)

Each module gets its own spec (`SPEC-auth.md`, etc.) after this master spec is approved.