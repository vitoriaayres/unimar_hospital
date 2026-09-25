"""Treino de modelo LightGBM para previsão de demanda.

Treina modelo, avalia com métricas reais, salva para produção.
"""

from __future__ import annotations

import io
import json
import pickle
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

# Adicionar diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lightgbm as lgb
import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ml.features import (
    build_features,
    load_consumption,
    load_inventory,
    load_products,
    prepare_train_test,
)
from ml.inference import predict_demand

MODEL_DIR = Path('ml/models')
METRICS_DIR = Path('ml/data')

VALIDATION_DAYS = 180
BLEND_GRID = np.arange(0.0, 1.05, 0.05)

PARAMS = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'num_leaves': 255,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'min_child_samples': 10,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'verbose': -1,
    'n_jobs': -1,
}


def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_valid: pd.DataFrame,
    y_valid: np.ndarray,
) -> lgb.Booster:
    """Treina LightGBM em escala log1p com early stopping na validacao temporal."""
    train_data = lgb.Dataset(X_train, label=np.log1p(np.maximum(y_train, 0)))
    valid_data = lgb.Dataset(X_valid, label=np.log1p(np.maximum(y_valid, 0)), reference=train_data)

    model = lgb.train(
        PARAMS,
        train_data,
        num_boost_round=3000,
        valid_sets=[valid_data],
        valid_names=['valid'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=100),
            lgb.log_evaluation(period=200),
        ],
    )
    return model


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, baseline: np.ndarray) -> dict:
    """Metricas no teste: erro relativo, por faixa de volume e vs baseline."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.maximum(np.asarray(y_pred, dtype=float), 0)
    baseline = np.maximum(np.asarray(baseline, dtype=float), 0)

    bands = np.quantile(y_true, [1 / 3, 2 / 3])
    masks = {
        'low': y_true < bands[0],
        'mid': (y_true >= bands[0]) & (y_true < bands[1]),
        'high': y_true >= bands[1],
    }

    def wape(y, p):
        return float(np.abs(y - p).sum() / y.sum()) if y.sum() else float('nan')

    def mape(y, p):
        return float(np.mean(np.abs(y - p) / y)) if len(y) else float('nan')

    metrics = {
        'mape': round(mape(y_true, y_pred), 6),
        'smape': round(
            float(np.mean(2 * np.abs(y_true - y_pred) / (np.abs(y_true) + np.abs(y_pred) + 1e-8))),
            6,
        ),
        'wape': round(wape(y_true, y_pred), 6),
        'rmse': round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        'mae': round(float(mean_absolute_error(y_true, y_pred)), 4),
        'baseline_wape': round(wape(y_true, baseline), 6),
        'baseline_mape': round(mape(y_true, baseline), 6),
    }
    for name, mask in masks.items():
        metrics[f'mape_{name}'] = round(mape(y_true[mask], y_pred[mask]), 6)
        metrics[f'wape_{name}'] = round(wape(y_true[mask], y_pred[mask]), 6)
    return metrics


def tune_blend_weight(model: lgb.Booster, X_valid: pd.DataFrame, y_valid: np.ndarray) -> float:
    """Escolhe o peso do blend modelo/baseline na validacao (nao no teste)."""
    raw = np.maximum(np.expm1(model.predict(X_valid)), 0)
    baseline = np.maximum(np.nan_to_num(np.asarray(X_valid['rolling_mean_7'], dtype=float)) * 7, 0)
    best_weight, best_wape = 0.5, float('inf')
    for weight in BLEND_GRID:
        score = wape_score(y_valid, weight * raw + (1 - weight) * baseline)
        if score < best_wape:
            best_weight, best_wape = float(weight), score
    print(f'  Blend otimizado na validacao: peso={best_weight:.2f} (WAPE {best_wape * 100:.2f}%)')
    return best_weight


def wape_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    return float(np.abs(y_true - y_pred).sum() / y_true.sum())


def save_model(model: lgb.Booster, metrics: dict, feature_cols: list[str]) -> Path:
    """Salva modelo + metadados para produção."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    model_path = MODEL_DIR / f'lightgbm_{timestamp}.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    metrics_path = METRICS_DIR / f'metrics_{timestamp}.json'
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    features_path = METRICS_DIR / f'features_{timestamp}.json'
    with open(features_path, 'w') as f:
        json.dump(feature_cols, f, indent=2)

    prod_model = MODEL_DIR / 'model_production.pkl'
    prod_features = METRICS_DIR / 'features_production.json'
    prod_metrics = METRICS_DIR / 'metrics_production.json'

    with open(prod_model, 'wb') as f:
        pickle.dump(model, f)
    with open(prod_features, 'w') as f:
        json.dump(feature_cols, f, indent=2)
    with open(prod_metrics, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f'  Modelo timestamp: {model_path}')
    print(f'  Modelo produção:  {prod_model}')
    print(f'  Métricas:         {prod_metrics}')

    return model_path


def print_feature_importance(model: lgb.Booster, feature_cols: list[str], top_n: int = 15) -> None:
    """Imprime feature importance."""
    importance = model.feature_importance(importance_type='gain')
    df = pd.DataFrame(
        {
            'feature': feature_cols,
            'importance': importance,
        }
    ).sort_values('importance', ascending=False)

    print(f'\n  Top {top_n} Features:')
    for i, (_, row) in enumerate(df.head(top_n).iterrows(), 1):
        bar = '\u2588' * int(row['importance'] / df['importance'].max() * 20)
        print(f'    {i:2d}. {row["feature"]:30s} {row["importance"]:>12.0f}  {bar}')


def main() -> None:
    print('=== Treino LightGBM ===\n')

    print('1. Carregando dados...')
    consumption = load_consumption()
    products = load_products()
    inventory = load_inventory()

    print('\n2. Construindo features...')
    features = build_features(consumption, products, inventory)

    print('\n3. Preparando train/test split...')
    train, test, feature_cols = prepare_train_test(features)

    # Validacao temporal: ultimos dias do treino (o teste fica intacto)
    valid_cutoff = train['consumption_date'].max() - timedelta(days=VALIDATION_DAYS)
    inner_train = train.filter(pl.col('consumption_date') < valid_cutoff)
    valid = train.filter(pl.col('consumption_date') >= valid_cutoff)
    print(
        f'  Validacao temporal: {valid_cutoff} em diante '
        f'({len(inner_train):,} treino / {len(valid):,} validacao)'
    )

    X_train = inner_train.select(feature_cols).to_pandas()
    y_train = inner_train.select('target_7d').to_numpy().ravel()
    X_valid = valid.select(feature_cols).to_pandas()
    y_valid = valid.select('target_7d').to_numpy().ravel()
    X_test = test.select(feature_cols).to_pandas()
    y_test = test.select('target_7d').to_numpy().ravel()

    print(f'  X_train: {X_train.shape}, y_train: {y_train.shape}')
    print(f'  X_valid: {X_valid.shape}, y_valid: {y_valid.shape}')
    print(f'  X_test:  {X_test.shape}, y_test: {y_test.shape}')

    print('\n4. Treinando LightGBM (alvo log1p)...')
    model = train_lightgbm(X_train, y_train, X_valid, y_valid)

    print('\n5. Otimizando blend modelo/baseline na validacao...')
    blend_weight = tune_blend_weight(model, X_valid, y_valid)

    y_pred = predict_demand(model, X_test, blend_weight)
    baseline = np.maximum(np.nan_to_num(X_test['rolling_mean_7'].to_numpy()) * 7, 0)

    metrics = compute_metrics(y_test, y_pred, baseline)
    metrics.update(
        {
            'model_type': 'lightgbm',
            'objective': 'regression_log1p',
            'blend_weight': blend_weight,
            'target': 'consumption_next_7d_sum',
            'n_features': X_train.shape[1],
            'n_train': X_train.shape[0],
            'n_valid': X_valid.shape[0],
            'n_test': X_test.shape[0],
            'best_iteration': model.best_iteration,
            'trained_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        }
    )

    print('\n=== Metricas (teste) ===')
    print(f'  WAPE:       {metrics["wape"] * 100:.2f}%')
    print(f'  MAPE:       {metrics["mape"] * 100:.2f}%')
    print(f'  sMAPE:      {metrics["smape"] * 100:.2f}%')
    print(f'  RMSE:       {metrics["rmse"]:.2f}')
    print(f'  MAE:        {metrics["mae"]:.2f}')
    print(f'  Iteracoes:  {metrics["best_iteration"]}')
    print('\n  Por faixa de demanda (MAPE / WAPE):')
    for band in ('low', 'mid', 'high'):
        print(
            f'    {band:5s}  {metrics[f"mape_{band}"] * 100:6.2f}% / '
            f'{metrics[f"wape_{band}"] * 100:6.2f}%'
        )
    print('\n  Baseline (rolling_mean_7 * 7):')
    print(
        f'    WAPE {metrics["baseline_wape"] * 100:.2f}%  MAPE {metrics["baseline_mape"] * 100:.2f}%'
    )
    delta = (metrics['baseline_wape'] - metrics['wape']) * 100
    print(f'    Ganho do modelo: {delta:+.2f} p.p. de WAPE')

    target_wape = 0.15
    status = 'OK' if metrics['wape'] < target_wape else 'NEEDS IMPROVEMENT'
    print(
        f'\n  WAPE ({metrics["wape"] * 100:.2f}%) vs target ({target_wape * 100:.0f}%) - {status}'
    )

    print('\n6. Salvando modelo...')
    save_model(model, metrics, feature_cols)

    print_feature_importance(model, feature_cols)

    print('\n=== Treino Concluído ===')


if __name__ == '__main__':
    main()
