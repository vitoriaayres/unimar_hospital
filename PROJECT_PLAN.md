# Project Plan: PharmaPredict - 10 Weeks, 7 People

## Team Roles & Assignments

| Person | Primary Role | Secondary | Modules Owned |
|--------|-------------|-----------|---------------|
| **P1** | Tech Lead / Backend Architect | DevOps | `auth`, `catalog`, CI/CD, Infra |
| **P2** | Backend Engineer | ML Pipeline | `inventory`, `consumption`, ML integration |
| **P3** | Backend Engineer | API Design | `predictions`, `alerts`, OpenAPI |
| **P4** | ML Engineer (Lead) | Data Engineering | `forecasting` (data gen, features, training) |
| **P5** | ML Engineer | MLOps | `forecasting` (evaluation, serving, monitoring) |
| **P6** | Frontend Lead | UX/UI | `dashboard` (layout, charts, state) |
| **P7** | Frontend Engineer | Testing | `dashboard` (pages, forms, E2E tests) |

---

## Sprint Breakdown (2-week sprints)

### Sprint 0: Foundation (Week 1) — *All hands on deck*

| Task | Owner | Deliverable |
|------|-------|-------------|
| Initialize repos (backend, frontend) with tooling | P1 | `uv init`, `create-next-app`, lint, typecheck, test configs |
| Docker Compose dev stack (PG, Redis, MLflow, MinIO) | P1 | `docker-compose.yml` + healthchecks |
| GitHub Actions CI (lint, typecheck, test, build) | P1 | `.github/workflows/ci.yml` |
| Database schema (Alembic initial migration) | P1 + P2 | `alembic/versions/001_initial.py` |
| Design system setup (Tailwind, shadcn/ui, theme) | P6 | `frontend/src/components/ui/*` |
| API client + auth helpers (frontend) | P7 | `frontend/src/lib/api.ts`, `auth.ts` |
| **Sprint Review Demo** | All | Running dev stack, green CI, blank dashboard |

---

### Sprint 1: Core Domain (Week 2-3)

#### Week 2: Auth + Catalog

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| `auth`: User model, JWT tokens, bcrypt, roles | P1 | Login/register works; tokens refresh; RBAC enforced |
| `auth`: API routes `/auth/login`, `/auth/refresh`, `/auth/me` | P1 | OpenAPI documented; 100% unit test coverage |
| `catalog`: Product CRUD + search + pagination | P2 | CRUD API; filters (category, controlled, stock); tests |
| `catalog`: ATC code hierarchy + validation | P2 | Seed script with 500 synthetic products |
| Frontend: Login page + protected routes | P6 | Redirects work; JWT stored securely; logout |
| Frontend: Product list page (table + search) | P7 | Server-side pagination; debounced search; loading states |

#### Week 3: Inventory Core

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| `inventory`: Batch model, stock movements, FEFO logic | P2 | Movements update batch qty; expiry tracking; audit log |
| `inventory`: Receipt/dispense/adjustment APIs | P2 | Atomic transactions; validation; tests |
| `inventory`: Low stock / expiry queries | P2 | Dashboard service methods; < 100ms |
| Frontend: Inventory page (batches, expiries, movements) | P6 | TanStack Table; column filters; export CSV |
| Frontend: Batch detail modal (movements timeline) | P7 | Real-time updates via polling; accessible |

**Integration Point:** P2 ↔ P6/P7 sync on API contracts (OpenAPI → TypeScript types)

---

### Sprint 2: Consumption + ML Foundation (Week 4-5)

#### Week 4: Consumption History + Data Generation

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| `consumption`: Model + import API (CSV/Excel) | P3 | Bulk import; validation; idempotent; progress |
| `consumption`: Query API (filters, aggregation) | P3 | Department, date range, product; < 200ms |
| ML: Synthetic data generator v1 (config-driven) | P4 | Generates 3 years data in < 5 min; YAML config |
| ML: Feature engineering pipeline (Polars) | P4 | Outputs Parquet feature store; reproducible |
| ML: MLflow setup + experiment tracking | P5 | UI accessible; autolog works for sklearn/LGBM |
| Frontend: Consumption history page (charts + table) | P6 | Recharts line chart; date picker; department filter |

#### Week 5: Baseline Models + Training Pipeline

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| ML: Seasonal Naive + ETS baselines | P4 | Trained via MLflow; metrics logged |
| ML: TimeSeriesSplit CV framework | P4 | 4 folds expanding window; configurable |
| ML: LightGBM training + Optuna HPO | P5 | Best params saved; model registered in MLflow |
| ML: Evaluation scripts (MAPE, sMAPE, coverage) | P5 | Generates comparison plots; threshold checks |
| Backend: Prediction model + repository | P3 | CRUD for predictions; model_version field |
| Frontend: Model comparison page (admin) | P7 | Table with metrics; promote to staging button |

**Key Decision:** Freeze feature set after Week 5 based on baseline results

---

### Sprint 3: Predictions + Alerts (Week 6-7)

#### Week 6: Prediction Serving

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Backend: InferenceService (load from MLflow, cache) | P3 | < 100ms/batch; hot-swap version; tests |
| Backend: Daily batch prediction Celery task | P3 | Runs 02:00; processes 500 SKUs in < 60s |
| Backend: `/predictions` API (fresh + cached) | P3 | Query params: product, horizon, model_version |
| ML: Prediction intervals (quantile regression) | P4 | 80% coverage calibrated; logged in MLflow |
| Frontend: Product detail page with forecast chart | P6 | Historical + forecast; confidence band; hover |
| Frontend: Predictions page (all products table) | P7 | Sortable by risk; filter by model version |

#### Week 7: Alert Engine

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Backend: AlertService (shortage, expiry, overstock) | P2 | Rules engine; severity; acknowledgment flow |
| Backend: Alert evaluation Celery task (every 15m) | P2 | Checks stock + predictions; creates alerts |
| Backend: `/alerts` API (list, acknowledge, rules) | P3 | Pagination; filters; WebSocket-ready |
| ML: Shortage classification threshold tuning | P5 | Precision > 80%, Recall > 70% on backtest |
| Frontend: Alerts page (dashboard widget + full page) | P6 | Color-coded severity; bulk acknowledge; toast |
| Frontend: Alert rules configuration (manager only) | P7 | Form with Zod validation; threshold sliders |

---

### Sprint 4: Dashboard + Reports (Week 8-9)

#### Week 8: Executive Dashboard

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Backend: DashboardService (KPIs, aggregates) | P1 | Total SKUs, stockout risk count, expiring soon, value |
| Backend: Dashboard API (cached, 30s revalidate) | P1 | < 200ms; includes trend sparklines |
| Frontend: Main dashboard (KPI cards + charts) | P6 | Responsive grid; real-time feel; loading skeletons |
| Frontend: Stockout risk heatmap (calendar view) | P6 | Month view; color intensity = risk level |
| Frontend: Expiry timeline (Gantt-style) | P7 | Horizontal bars; filter by category; export |
| Frontend: Mobile-responsive layout (tablet) | P7 | Breakpoints 768/1024; touch-friendly |

#### Week 9: Reports + Polish

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Backend: ReportService (PDF via WeasyPrint, Excel) | P3 | Scheduled + on-demand; template system |
| Backend: Report templates (stock, expiries, forecast) | P3 | Professional layout; hospital branding |
| Backend: Email/notification stub for reports | P1 | Logs to console; ready for SMTP |
| Frontend: Reports page (schedule, history, download) | P6 | React Hook Form + Zod; date range picker |
| Frontend: Settings page (preferences, profile) | P7 | Theme toggle; notification prefs; password |
| All: Accessibility audit (axe-core) | P6/P7 | 0 violations; keyboard nav; screen reader |

---

### Sprint 5: Hardening + Launch (Week 10)

| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Load testing (k6: 50 concurrent users) | P1 | P95 < 300ms; 0 errors |
| Security audit (dependencies, auth, headers) | P1 | `npm audit`/`uv audit` clean; CSP headers |
| E2E test suite (Playwright: 10 critical flows) | P7 | Login→Dashboard→Alert→Report; CI integration |
| Documentation (API, user guide, deployment) | P1 + P6 | `docs/` complete; diagrams current |
| Demo preparation (script, synthetic data reset) | All | 15-min demo flows smoothly |
| **Final Demo & Retrospective** | All | Stakeholder presentation; lessons learned |

---

## Parallel Work Streams (Dependency Graph)

```
WEEK 1          WEEK 2-3         WEEK 4-5          WEEK 6-7          WEEK 8-9         WEEK 10
├─ Foundation   ├─ Auth          ├─ Consumption    ├─ Predictions    ├─ Dashboard     ├─ Hardening
│               ├─ Catalog       ├─ Data Gen       ├─ Alerts         ├─ Reports       └─ Demo
│               └─ Inventory     └─ ML Baseline    └─ ML Serving     └─ Polish
                      │              │                 │                │
                      ▼              ▼                 ▼                ▼
               ┌─────────────────────────────────────────────────────────────┐
               │                    ML PIPELINE (P4+P5)                      │
               │  Data Gen → Features → Baseline → LGBM/XGB → Eval → Serve  │
               │                    (continuous, feeds Sprints 2-4)          │
               └─────────────────────────────────────────────────────────────┘
```

---

## Daily Rituals

| Ritual | Time | Duration | Participants |
|--------|------|----------|--------------|
| **Standup** | 09:00 | 15 min | All 7 |
| **Backend Sync** | 11:00 | 30 min | P1, P2, P3 |
| **ML Sync** | 11:00 | 30 min | P4, P5 |
| **Frontend Sync** | 11:00 | 30 min | P6, P7 |
| **Integration Check** | 16:00 | 15 min | P2/P3 + P6/P7 |
| **Retro (Fri)** | 15:00 | 45 min | All |

---

## Risk Mitigation for 7-Person Team

| Risk | Mitigation |
|------|------------|
| **Merge conflicts** | Short-lived branches (< 2 days); rebase daily; CODEOWNERS per module |
| **API contract drift** | Generate TS types from Pydantic (`pydantic2ts`) in CI; fail build on mismatch |
| **ML ↔ Backend handoff** | Shared `schemas/prediction.py` → `types/api.ts`; contract tests in CI |
| **Knowledge silos** | Pair programming on integration points; rotate code review pairs weekly |
| **Scope creep** | SPEC.md change control; "Ask First" boundary; demo-driven feedback only |
| **ML experimentation rabbit hole** | Time-box: 2 days max per model variant; document negative results |

---

## Definition of Done (Per Task)

- [ ] Code compiles + passes typecheck (mypy strict / tsc --noEmit)
- [ ] Unit tests pass (≥ 85% backend, ≥ 80% frontend)
- [ ] Integration tests pass (testcontainers for DB)
- [ ] Lint clean (ruff / eslint)
- [ ] Documentation updated (docstrings, OpenAPI, README)
- [ ] Code reviewed by ≥ 1 other person (not author)
- [ ] Deployed to staging (auto on merge to develop)
- [ ] Manual verification by task owner + 1 peer

---

## Milestone Gates (Go/No-Go)

| Gate | Week | Criteria | Decision |
|------|------|----------|----------|
| **Foundation Ready** | 1 | Dev stack up; CI green; team can run locally | Go to Sprint 1 |
| **Core Domain Stable** | 3 | Auth + Catalog + Inventory CRUD working; tests pass | Go to Sprint 2 |
| **ML Baseline Beats Naive** | 5 | LightGBM MAPE < 15% on holdout; model in registry | Go to Sprint 3 |
| **Predictions Serving** | 7 | Daily batch runs; API < 200ms; frontend shows forecasts | Go to Sprint 4 |
| **Dashboard Usable** | 9 | KPIs load < 2s; alerts actionable; reports generate | Go to Sprint 5 |
| **Launch Ready** | 10 | Load test pass; security clean; E2E green; docs done | **LAUNCH** |

---

## Communication Channels

| Channel | Purpose | Tool |
|---------|---------|------|
| **Daily sync** | Blockers, progress | Discord/Teams voice |
| **Async updates** | PR reviews, decisions | GitHub Discussions |
| **Incidents** | Urgent production issues | WhatsApp group |
| **Documentation** | Specs, ADRs, decisions | Notion / GitHub Wiki |
| **Task tracking** | Sprint board, burndown | GitHub Projects / Linear |

---

## Budget & Resource Estimates (Dev Environment)

| Resource | Spec | Monthly Cost (Est.) |
|----------|------|---------------------|
| **Development** | Local (Docker Compose) | $0 |
| **Staging** | 1x t3.medium (2 vCPU, 4GB) + RDS db.t3.micro | ~$40 |
| **MLflow/MinIO** | Same instance (Docker) | Included |
| **Observability** | Prometheus/Grafana/Loki on staging | Included |
| **CI/CD** | GitHub Actions (2000 min/mo free) | $0 |
| **Total** | | **~$40/month** |

---

## Success Metrics (Project Level)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Velocity** | 35-40 story points/sprint | GitHub Projects |
| **Code Quality** | 0 critical SonarQube issues | SonarCloud |
| **Test Coverage** | Backend ≥ 85%, Frontend ≥ 80% | Codecov |
| **Deploy Frequency** | Daily to staging | GitHub Actions |
| **Lead Time** | < 2 days (PR → staging) | GitHub Metrics |
| **Bug Escape Rate** | 0 critical bugs in demo | Manual tally |
| **Team Satisfaction** | ≥ 4/5 retrospective score | Anonymous survey |

---

## Post-Launch Roadmap (Not in 10-week scope)

| Phase | Features | Effort |
|-------|----------|--------|
| **Phase 2** | Supplier integration (API/webhooks), Purchase order generation, Multi-warehouse transfers | 6 weeks |
| **Phase 3** | Mobile app (React Native), Offline support, Barcode scanning | 8 weeks |
| **Phase 4** | Multi-tenant (hospital network), ANVISA compliance module, Advanced analytics | 12 weeks |
| **ML v2** | Hierarchical forecasting, Causal inference, Real-time streaming features | Ongoing |

---

## Appendix: Quick Start Commands

```bash
# One-command dev setup (after cloning)
git clone <repo>
cd PharmaPredict
docker compose up -d                    # Postgres, Redis, MLflow, MinIO
cd backend && uv sync && uv run alembic upgrade head
cd ../frontend && npm install && npm run dev
# → Frontend: http://localhost:3000
# → Backend API: http://localhost:8000/docs
# → MLflow: http://localhost:5001

# Generate synthetic data & train baseline
cd backend && uv run python -m ml.generate_synthetic_data
cd backend && uv run python -m ml.train --model lightgbm --trials 20

# Run tests
cd backend && uv run pytest -xvs
cd frontend && npm run test && npm run test:e2e
```

---

*Document version: 1.0 | Last updated: Sprint 0 planning | Next review: End of Week 1*