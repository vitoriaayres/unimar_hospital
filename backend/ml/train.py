"""Treino de modelo LightGBM para previsão de demanda.

Treina modelo, avalia com métricas reais, salva para produção.
"""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime
from pathlib import Path

# Adicionar diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error

from ml.features import (
    load_consumption,
    load_inventory,
    load_products,
    build_features,
    prepare_train_test,
)

MODEL_DIR = Path("ml/models")
METRICS_DIR = Path("ml/data")


def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
) -> tuple[lgb.Booster, dict, np.ndarray]:
    """Treina LightGBM com early stopping e retorna modelo + métricas."""

    params = {
        "objective": "regression",
        "metric": "rmse",  # Use RMSE for training (more stable than MAPE)
        "boosting_type": "gbdt",
        "num_leaves": 127,
        "learning_rate": 0.03,
        "feature_fraction": 0.7,
        "bagging_fraction": 0.7,
        "bagging_freq": 5,
        "min_child_samples": 20,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "verbose": -1,
        "n_jobs": -1,
    }

    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    callbacks = [
        lgb.early_stopping(stopping_rounds=100),
        lgb.log_evaluation(period=100),
    ]

    model = lgb.train(
        params,
        train_data,
        valid_sets=[train_data, test_data],
        valid_names=["train", "test"],
        num_boost_round=2000,
        callbacks=callbacks,
    )

    y_pred = model.predict(X_test)
    y_pred = np.maximum(y_pred, 0)

    # Filter out zero actuals for MAPE (MAPE undefined at zero)
    # Also filter very low demand (unstable MAPE)
    nonzero_mask = y_test > 5  # Only products with >5 units actual
    if nonzero_mask.sum() > 0:
        mape = mean_absolute_percentage_error(y_test[nonzero_mask], y_pred[nonzero_mask])
    else:
        mape = float('inf')
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae = float(mean_absolute_error(y_test, y_pred))
    smape_val = float(np.mean(2 * np.abs(y_test - y_pred) / (np.abs(y_test) + np.abs(y_pred) + 1e-8)))

    metrics = {
        "model_type": "lightgbm",
        "mape": round(float(mape), 6),
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "smape": round(smape_val, 6),
        "n_features": X_train.shape[1],
        "n_train": X_train.shape[0],
        "n_test": X_test.shape[0],
        "best_iteration": model.best_iteration,
        "trained_at": datetime.utcnow().isoformat() + "Z",
    }

    return model, metrics, y_pred


def save_model(model: lgb.Booster, metrics: dict, feature_cols: list[str]) -> Path:
    """Salva modelo + metadados para produção."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    model_path = MODEL_DIR / f"lightgbm_{timestamp}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    metrics_path = METRICS_DIR / f"metrics_{timestamp}.json"
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    features_path = METRICS_DIR / f"features_{timestamp}.json"
    with open(features_path, "w") as f:
        json.dump(feature_cols, f, indent=2)

    prod_model = MODEL_DIR / "model_production.pkl"
    prod_features = METRICS_DIR / "features_production.json"
    prod_metrics = METRICS_DIR / "metrics_production.json"

    with open(prod_model, "wb") as f:
        pickle.dump(model, f)
    with open(prod_features, "w") as f:
        json.dump(feature_cols, f, indent=2)
    with open(prod_metrics, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"  Modelo timestamp: {model_path}")
    print(f"  Modelo produção:  {prod_model}")
    print(f"  Métricas:         {prod_metrics}")

    return model_path


def print_feature_importance(model: lgb.Booster, feature_cols: list[str], top_n: int = 15) -> None:
    """Imprime feature importance."""
    importance = model.feature_importance(importance_type="gain")
    df = pd.DataFrame({
        "feature": feature_cols,
        "importance": importance,
    }).sort_values("importance", ascending=False)

    print(f"\n  Top {top_n} Features:")
    for i, (_, row) in enumerate(df.head(top_n).iterrows(), 1):
        bar = "\u2588" * int(row["importance"] / df["importance"].max() * 20)
        print(f"    {i:2d}. {row['feature']:30s} {row['importance']:>12.0f}  {bar}")


def main() -> None:
    print("=== Treino LightGBM ===\n")

    print("1. Carregando dados...")
    consumption = load_consumption()
    products = load_products()
    inventory = load_inventory()

    print("\n2. Construindo features...")
    features = build_features(consumption, products, inventory)

    print("\n3. Preparando train/test split...")
    train, test, feature_cols = prepare_train_test(features)

    X_train = train.select(feature_cols).to_pandas()
    y_train = train.select("target_7d").to_pandas().values.ravel()
    X_test = test.select(feature_cols).to_pandas()
    y_test = test.select("target_7d").to_pandas().values.ravel()

    print(f"  X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"  X_test:  {X_test.shape}, y_test:  {y_test.shape}")

    print("\n4. Treinando LightGBM...")
    model, metrics, y_pred = train_lightgbm(X_train, y_train, X_test, y_test)

    print("\n=== Metricas ===")
    print(f"  MAPE:  {metrics['mape']:.4f} ({metrics['mape']*100:.2f}%)")
    print(f"  sMAPE: {metrics['smape']:.4f} ({metrics['smape']*100:.2f}%)")
    print(f"  RMSE:  {metrics['rmse']:.2f}")
    print(f"  MAE:   {metrics['mae']:.2f}")
    print(f"  Iterações: {metrics['best_iteration']}")

    target_mape = 0.15
    if metrics["mape"] < target_mape:
        print(f"\n  MAPE ({metrics['mape']*100:.2f}%) < target ({target_mape*100:.0f}%) OK")
    else:
        print(f"\n  MAPE ({metrics['mape']*100:.2f}%) >= target ({target_mape*100:.0f}%) - NEEDS IMPROVEMENT")

    print("\n5. Salvando modelo...")
    save_model(model, metrics, feature_cols)

    print_feature_importance(model, feature_cols)

    print("\n=== Treino Concluído ===")


if __name__ == "__main__":
    main()
