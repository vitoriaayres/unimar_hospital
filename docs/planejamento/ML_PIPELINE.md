# ML Pipeline Specification: PharmaPredict

## Overview

This document details the machine learning pipeline for demand forecasting, including synthetic data generation, feature engineering, model training, evaluation, and serving. The pipeline is designed to be **reproducible**, **experiment-tracked**, and **production-ready** from day one.

---

## 1. Synthetic Data Generation

### 1.1 Design Principles

Since real hospital data is unavailable, we generate **realistic synthetic data** that captures known patterns in hospital pharmacy consumption:

| Pattern | Source | Implementation |
|---------|--------|----------------|
| **Seasonality** | Literature (WHO, Brazilian hospital studies) | Fourier series (3 harmonics) + Brazilian holiday calendar |
| **Drug-class trends** | ATC classification consumption patterns | Class-specific ARIMA-like base + noise |
| **Department mix** | Hospital operations research | Dirichlet distribution per drug class |
| **Stockout cascades** | Supply chain literature | Hawkes process (self-exciting) |
| **Expiry-driven consumption** | FEFO/FIFO practice | Priority logic in movement simulator |
| **Supplier lead time** | Procurement data | Log-normal per supplier tier |

### 1.2 Configuration (YAML)

```yaml
# ml/config/data_generation.yaml
simulation:
  start_date: "2021-01-01"
  end_date: "2024-12-31"
  random_seed: 42

hospital:
  name: "Hospital Municipal São José"
  beds: 350
  departments:
    - id: "icu"
      name: "UTI Geral"
      weight: 0.15
      consumption_multiplier: 1.8
    - id: "er"
      name: "Pronto Socorro"
      weight: 0.25
      consumption_multiplier: 1.3
    - id: "ward"
      name: "Enfermarias"
      weight: 0.45
      consumption_multiplier: 1.0
    - id: "outpatient"
      name: "Ambulatório"
      weight: 0.15
      consumption_multiplier: 0.6

products:
  count: 500
  atc_distribution:
    "J01": 0.20   # Antibiotics
    "N02": 0.15   # Analgesics
    "B01": 0.10   # Antithrombotics
    "C07": 0.08   # Beta blockers
    "A02": 0.08   # PPIs
    "R03": 0.07   # Bronchodilators
    "N05": 0.06   # Psycholeptics
    "C09": 0.05   # ACE inhibitors
    "H02": 0.04   # Corticosteroids
    "OTHER": 0.17
  
  # Per-class base demand (units/day per 100 beds)
  class_base_demand:
    "J01": 45
    "N02": 60
    "B01": 25
    "C07": 30
    "A02": 35
    "R03": 20
    "N05": 15
    "C09": 28
    "H02": 12

seasonality:
  enabled: true
  fourier_terms: 3
  holidays_br:
    - "Carnaval"
    - "Semana Santa"
    - "Tiradentes"
    - "Dia do Trabalho"
    - "Corpus Christi"
    - "Independência"
    - "Nossa Senhora Aparecida"
    - "Finados"
    - "Proclamação da República"
    - "Natal"
  holiday_window_days: 3
  holiday_effect: 0.3  # 30% increase

suppliers:
  count: 12
  tiers:
    - name: "national_distributor"
      count: 4
      lead_time_days: {mean: 5, std: 2}
      reliability: 0.95
    - name: "regional_distributor"
      count: 5
      lead_time_days: {mean: 3, std: 1}
      reliability: 0.92
    - name: "manufacturer_direct"
      count: 3
      lead_time_days: {mean: 10, std: 5}
      reliability: 0.88

inventory_policy:
  review_period_days: 7
  service_level: 0.95
  safety_stock_method: "demand_variability"
  fefo_enabled: true
  expiry_alert_days: 90

consumption_noise:
  distribution: "negative_binomial"  # Overdispersed count data
  dispersion: 1.5
  zero_inflation: 0.05  # Days with no consumption

stockout_cascade:
  enabled: true
  hawkes_baseline: 0.001
  hawkes_alpha: 0.3
  hawkes_beta: 0.1
  emergency_order_multiplier: 2.0
  emergency_lead_time_reduction: 0.5
```

### 1.3 Generation Algorithm

```python
# ml/generate_data.py (simplified structure)
class SyntheticDataGenerator:
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.rng = np.random.default_rng(config.simulation.random_seed)
    
    def generate(self) -> SyntheticDataset:
        # 1. Generate product catalog with ATC hierarchy
        products = self._generate_products()
        
        # 2. Generate supplier catalog
        suppliers = self._generate_suppliers()
        
        # 3. Simulate daily consumption per product per department
        consumption = self._simulate_consumption(products)
        
        # 4. Simulate inventory movements (receipts, dispenses, adjustments)
        inventory = self._simulate_inventory(products, suppliers, consumption)
        
        # 5. Generate stockout events and emergency orders
        stockouts = self._simulate_stockouts(inventory, consumption)
        
        return SyntheticDataset(
            products=products,
            suppliers=suppliers,
            consumption=consumption,
            inventory=inventory,
            stockouts=stockouts,
        )
    
    def _simulate_consumption(self, products: list[Product]) -> pl.DataFrame:
        """Vectorized simulation using Polars for performance."""
        date_range = pl.date_range(
            self.config.simulation.start_date,
            self.config.simulation.end_date,
            interval="1d",
            eager=True
        )
        
        # Base demand per product (with class seasonality)
        base_demand = self._compute_base_demand(products, date_range)
        
        # Add department mix
        dept_mix = self._sample_department_mix(products)
        
        # Apply holiday effects
        holiday_effect = self._compute_holiday_effect(date_range)
        
        # Sample from negative binomial
        consumption = self._sample_consumption(base_demand, dept_mix, holiday_effect)
        
        return consumption
```

### 1.4 Output Schema

| Table | Rows (3 years) | Key Columns |
|-------|----------------|-------------|
| `product` | 500 | id, sku, name, atc_code, class_base_demand, min/max_stock, lead_time |
| `supplier` | 12 | id, name, tier, lead_time_dist, reliability |
| `consumption` | ~500k | product_id, date, department, quantity, prescription_type |
| `inventory_batch` | ~15k | product_id, batch_number, quantity, expiry_date, status |
| `stock_movement` | ~600k | batch_id, quantity_change, movement_type, reference_id, timestamp |
| `stockout_event` | ~2k | product_id, start_date, end_date, severity, emergency_order_qty |

---

## 2. Feature Engineering

### 2.1 Feature Categories

| Category | Features | Window/Config |
|----------|----------|---------------|
| **Lag Features** | Consumption t-1, t-7, t-14, t-30, t-60, t-90 | 6 lags |
| **Rolling Statistics** | Mean, std, min, max, median, skew | Windows: 7, 14, 30, 60, 90 |
| **Expanding Statistics** | Cumulative mean, std, trend (Theil-Sen) | All history |
| **Calendar** | Day of week, week of month, month, quarter, is_holiday, days_to_holiday, days_after_holiday | Brazilian calendar |
| **Product Embeddings** | ATC level 1-4 one-hot, class_base_demand_log, unit_cost_log, lead_time_log, controlled_substance | Static per product |
| **Stock Features** | Current stock, days_of_supply, stock_to_max_ratio, batches_expiring_30d, batches_expiring_90d | Current snapshot |
| **Supplier Features** | Avg lead time, reliability, tier encoding | Static per supplier |
| **Interaction** | Lag × department, stock × seasonality | Selected via importance |

### 2.2 Feature Store Design

```
feature_store/
├── consumption_features.parquet    # Partitioned by date (monthly)
├── inventory_features.parquet      # Partitioned by date (weekly)
├── product_features.parquet        # Static, full refresh weekly
├── supplier_features.parquet       # Static
└── metadata.json                   # Feature descriptions, versions, stats
```

**Metadata Example:**
```json
{
  "version": "2024.1",
  "generated_at": "2024-01-15T10:30:00Z",
  "features": {
    "consumption_lag_7": {
      "type": "numeric",
      "description": "Consumption 7 days ago",
      "stats": {"mean": 42.3, "std": 18.7, "missing_rate": 0.02}
    }
  },
  "target": "consumption_quantity",
  "target_horizon_days": [1, 7, 14, 30]
}
```

---

## 3. Model Training

### 3.1 Model Zoo

| Model | Type | Use Case | Training Time | Inference Latency |
|-------|------|----------|---------------|-------------------|
| **Seasonal Naive** | Baseline | Benchmark | < 1s | < 1ms |
| **ETS (Exponential Smoothing)** | Statistical | Strong seasonality | < 5s | < 1ms |
| **LightGBM** | Gradient Boosting | Primary production | 30-60s | ~5ms |
| **XGBoost** | Gradient Boosting | Comparison / ensemble | 45-90s | ~8ms |
| **Random Forest** | Ensemble | Robustness check | 60-120s | ~10ms |
| **LSTM** | Deep Learning | Complex sequences | 5-15 min | ~20ms |
| **Temporal Fusion Transformer** | Deep Learning | Multi-horizon + interpretability | 10-30 min | ~50ms |

### 3.2 Cross-Validation Strategy

**Time Series Split (Expanding Window):**
```
Fold 1: Train [2021-01 to 2022-06] → Test [2022-07 to 2022-12]
Fold 2: Train [2021-01 to 2022-12] → Test [2023-01 to 2023-06]
Fold 3: Train [2021-01 to 2023-06] → Test [2023-07 to 2023-12]
Fold 4: Train [2021-01 to 2023-12] → Test [2024-01 to 2024-06]
```

**Why not random split?** Temporal leakage would inflate metrics. Expanding window mimics production: train on all history, predict future.

### 3.3 Hyperparameter Optimization

```python
# ml/train.py (Optuna integration)
def objective(trial: optuna.Trial) -> float:
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 200, 2000, step=100),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "num_leaves": trial.suggest_int("num_leaves", 15, 255),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
    }
    
    model = LGBMRegressor(**params, random_state=42, n_jobs=-1, verbosity=-1)
    
    # Time series CV
    tscv = TimeSeriesSplit(n_splits=4, test_size=180, gap=7)
    scores = cross_val_score(model, X, y, cv=tscv, scoring="neg_mean_absolute_percentage_error", n_jobs=-1)
    
    return -scores.mean()  # Optuna minimizes
```

### 3.4 MLflow Experiment Structure

```
Experiment: "pharmapredict-demand-forecasting"
├── Run: "lightgbm_v1_baseline"
│   ├── Params: {...}
│   ├── Metrics: {mape: 0.12, rmse: 8.5, mae: 5.2, smape: 0.11}
│   ├── Artifacts: model.pkl, feature_importance.png, residuals.png
│   └── Tags: {"model_type": "lightgbm", "stage": "staging"}
├── Run: "xgboost_v1_tuned"
├── Run: "lstm_v1_sequence_90"
└── Run: "ensemble_v1_weighted"
```

**Model Registry Promotion:**
```
Staging → (automated validation) → Production
  Criteria: MAPE < 0.15 AND better than current production
```

---

## 4. Model Evaluation

### 4.1 Metrics Dashboard

| Metric | Formula | Target | Interpretation |
|--------|---------|--------|----------------|
| **MAPE** | `mean(|actual - pred| / actual)` | < 15% | Relative error, scale-independent |
| **sMAPE** | `2 * mean(|actual - pred| / (|actual| + |pred|))` | < 15% | Symmetric, handles zeros better |
| **RMSE** | `sqrt(mean((actual - pred)^2))` | Context-dependent | Penalizes large errors |
| **MAE** | `mean(|actual - pred|)` | Context-dependent | Robust, interpretable |
| **Coverage** | `% actual in [lower, upper]` | 80-90% | Prediction interval calibration |
| **Interval Width** | `mean(upper - lower)` | Minimize | Sharpness vs. coverage tradeoff |

### 4.2 Shortage Classification Metrics

Transform regression → classification for alerting:
- **Positive class:** Stockout within 7 days (simulated from inventory + predictions)
- **Threshold:** Predicted cumulative demand > current stock + safety stock

| Metric | Target | Why |
|--------|--------|-----|
| **Precision@7d** | > 80% | Few false alarms (pharmacist trust) |
| **Recall@7d** | > 70% | Catch most real shortages |
| **F1@7d** | > 75% | Balanced |
| **Lead Time** | Median ≥ 7 days | Actionable window |

### 4.3 Backtesting Protocol

```python
def backtest(model, data, horizon_days=30, n_splits=4):
    """Walk-forward backtest with expanding window."""
    results = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(data)):
        train_data = data.iloc[train_idx]
        test_data = data.iloc[test_idx]
        
        # Retrain on expanding window
        model.fit(train_data[features], train_data[target])
        
        # Predict horizon
        preds = predict_horizon(model, test_data, horizon_days)
        
        # Compute metrics per horizon day
        for h in range(1, horizon_days + 1):
            metrics = compute_metrics(test_data[target].shift(-h), preds[:, h-1])
            metrics["fold"] = fold
            metrics["horizon"] = h
            results.append(metrics)
    
    return pd.DataFrame(results)
```

---

## 5. Model Serving

### 5.1 Inference Service Architecture

```python
# ml/predict.py
class InferenceService:
    def __init__(self, model_registry: ModelRegistry, cache: RedisCache):
        self.registry = model_registry
        self.cache = cache
        self._model_cache: dict[str, BaseModel] = {}
    
    async def predict_batch(
        self,
        product_ids: list[UUID],
        horizon_days: int = 30,
        model_version: str | None = None,
    ) -> list[PredictionResult]:
        # 1. Check cache
        cache_key = f"predictions:{model_version or 'prod'}:{hash(tuple(product_ids))}:{horizon_days}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 2. Load model (cached in memory)
        model = await self._get_model(model_version)
        
        # 3. Build features for all products
        features = await self.feature_store.get_latest(product_ids)
        
        # 4. Predict
        predictions = model.predict(features, horizon_days)
        
        # 5. Format + cache (6h TTL)
        results = self._format_predictions(product_ids, predictions)
        await self.cache.set(cache_key, results, ttl=21600)
        
        return results
    
    async def _get_model(self, version: str | None) -> BaseModel:
        if version is None:
            version = await self.registry.get_production_version()
        
        if version not in self._model_cache:
            model_uri = await self.registry.get_model_uri(version)
            self._model_cache[version] = mlflow.pyfunc.load_model(model_uri)
        
        return self._model_cache[version]
```

### 5.2 Batch Prediction Job (Daily)

```python
# tasks/ml_tasks.py
@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_daily_predictions(self, horizon_days: int = 30):
    """Run daily at 02:00 via Celery Beat."""
    inference = InferenceService(registry, redis)
    products = await product_repo.get_all_active()
    
    # Batch in chunks of 50 to manage memory
    for chunk in chunked(products, 50):
        predictions = await inference.predict_batch(
            [p.id for p in chunk],
            horizon_days=horizon_days,
        )
        await prediction_repo.upsert_many(predictions)
    
    # Trigger alert evaluation
    evaluate_shortage_alerts.delay()
    
    return {"predictions_generated": len(products), "horizon_days": horizon_days}
```

### 5.3 Model Versioning & Hot Swap

```
MLflow Registry:
└── pharmapredict-demand
    ├── Version 1 (Production) → lightgbm_v3
    ├── Version 2 (Staging)    → xgboost_v2
    └── Version 3 (Archived)   → lstm_v1
```

- **Promotion:** Automated via evaluation pipeline; manual approval for Production
- **Rollback:** One-click in MLflow UI; InferenceService reloads on next request
- **A/B Testing:** `model_version` query param in `/predictions` endpoint

---

## 6. Monitoring & Drift Detection

### 6.1 Data Drift (Input Features)

```python
# monitoring/drift.py
def detect_feature_drift(
    reference: pd.DataFrame,  # Training feature distribution
    current: pd.DataFrame,    # Recent inference features
    threshold: float = 0.05,
) -> DriftReport:
    """Kolmogorov-Smirnov test per feature + population stability index."""
    report = {}
    for col in reference.select_dtypes(include=[np.number]).columns:
        ks_stat, p_value = ks_2samp(reference[col].dropna(), current[col].dropna())
        psi = population_stability_index(reference[col], current[col])
        
        report[col] = {
            "ks_statistic": ks_stat,
            "p_value": p_value,
            "psi": psi,
            "drift_detected": p_value < threshold or psi > 0.2,
        }
    
    return DriftReport(features=report, overall_drift=any(r["drift_detected"] for r in report.values()))
```

### 6.2 Prediction Drift (Concept Drift)

Monitor **MAPE on recent actuals** (when available) vs. training MAPE. Alert if degradation > 20%.

### 6.3 Operational Metrics

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Prediction latency P99 | > 500ms | Scale workers / optimize model |
| Cache hit rate | < 80% | Increase TTL / investigate |
| Model version age | > 14 days | Trigger retrain |
| Drift detected | Any feature | Notify ML engineer |
| Training job failure | Any | Alert on-call |

---

## 7. Reproducibility Checklist

- [ ] All random seeds fixed (numpy, torch, python, lightgbm)
- [ ] Environment pinned (`uv.lock`, `requirements.txt` via `uv export`)
- [ ] Data generation config versioned with code
- [ ] Feature engineering deterministic (no random sampling without seed)
- [ ] MLflow autolog enabled for all runs
- [ ] Model artifacts stored in versioned object store (MinIO/S3)
- [ ] Evaluation protocol code versioned (not just notebooks)
- [ ] Docker image includes model artifacts for reproducible serving

---

## 8. Week-by-Week ML Milestones

| Week | Deliverable | Owner |
|------|-------------|-------|
| 1 | Synthetic data generator v1 (config + basic patterns) | ML Eng 1 |
| 2 | Feature engineering pipeline + feature store (Parquet) | ML Eng 1 |
| 3 | Baseline models (Naive, ETS) + CV framework + MLflow | ML Eng 2 |
| 4 | LightGBM/XGBoost training + Optuna HPO | ML Eng 2 |
| 5 | Evaluation dashboard (metrics, plots, backtest) | ML Eng 1 |
| 6 | Inference service + Redis caching + API integration | ML Eng 1 + Backend |
| 7 | LSTM/Transformer experiments (stretch) | ML Eng 2 |
| 8 | Drift detection + monitoring alerts | ML Eng 1 |
| 9 | Model card documentation + final benchmarking | Both |
| 10 | Load testing + production hardening | Both |

---

## 9. Key Files to Create

```
backend/app/ml/
├── config/
│   ├── data_generation.yaml
│   ├── features.yaml
│   ├── lightgbm.yaml
│   ├── xgboost.yaml
│   └── lstm.yaml
├── generate_data.py
├── features.py
├── models/
│   ├── __init__.py
│   ├── baseline.py
│   ├── tree_based.py
│   └── deep_learning.py
├── train.py
├── evaluate.py
├── predict.py
├── registry.py
├── scheduler.py
└── monitoring/
    ├── __init__.py
    └── drift.py
```

---

## 10. Stretch Goals (If Time Permits)

1. **Probabilistic Forecasting:** Quantile regression (LightGBM `objective=quantile`) for native prediction intervals
2. **Hierarchical Forecasting:** Reconcile SKU-level forecasts with category-level totals
3. **Causal Features:** Incorporate known events (surgery schedules, epidemic alerts) as exogenous variables
4. **AutoML:** Full pipeline search (features + model + HPO) via Optuna + MLflow
5. **Explainability:** SHAP values per prediction for pharmacist trust
6. **Multi-horizon Loss:** Train directly for 1/7/14/30 day horizons with weighted loss