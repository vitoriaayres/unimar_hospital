"""Gera ml/data/model_report_production.json a partir do modelo ja treinado.

Usa o modelo de producao e o conjunto de teste salvos pelo pipeline, sem treinar de novo.
Util quando so o relatorio (tela "Modelo" e ml/report.py) precisa ser refeito.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

# Adicionar diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import polars as pl

from ml.inference import predict_demand, to_feature_frame
from ml.train import METRICS_DIR, MODEL_DIR, build_report, compute_metrics


def main() -> None:
    print('=== Relatorio do modelo (sem treino) ===\n')

    with open(MODEL_DIR / 'model_production.pkl', 'rb') as f:
        model = pickle.load(f)
    with open(METRICS_DIR / 'features_production.json') as f:
        feature_cols = json.load(f)
    with open(METRICS_DIR / 'metrics_production.json') as f:
        metrics = json.load(f)

    test = pl.read_parquet(METRICS_DIR / 'test.parquet')
    X_test = to_feature_frame(test, feature_cols)
    y_test = test.select('target_7d').to_numpy().ravel()

    y_pred = predict_demand(model, X_test, metrics['blend_weight'])
    baseline = np.maximum(np.nan_to_num(X_test['rolling_mean_7'].to_numpy()) * 7, 0)

    # Confere que o teste salvo reproduz as metricas do treino
    check = compute_metrics(y_test, y_pred, baseline)
    print(f'  WAPE recalculado: {check["wape"] * 100:.2f}% (treino: {metrics["wape"] * 100:.2f}%)')

    report = build_report(model, feature_cols, test, y_pred, baseline, metrics)
    report_path = METRICS_DIR / 'model_report_production.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f'  Relatorio: {report_path}')


if __name__ == '__main__':
    main()
