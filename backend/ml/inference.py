"""Inferencia em producao.

O alvo do modelo e a soma do consumo dos proximos 7 dias, treinado em escala
log1p. A predicao final combina o modelo com um baseline de media movel de 7
dias, que reduz a variancia em produtos de baixo volume.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl

# Peso do modelo na combinacao (otimizado na validacao temporal, ver ml/train.py)
BLEND_WEIGHT = 0.5


def to_feature_frame(df: pl.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Matriz de features em pandas (float64) sem depender do pyarrow.

    Todas as features sao numericas; nulos viram NaN, como o LightGBM espera.
    """
    values = df.select(pl.col(feature_cols).cast(pl.Float64)).to_numpy()
    return pd.DataFrame(values, columns=feature_cols)


def predict_demand(model, X, blend_weight: float = BLEND_WEIGHT) -> np.ndarray:
    """Retorna a previsao de consumo total dos proximos 7 dias."""
    raw = np.maximum(np.expm1(model.predict(X)), 0.0)

    columns = getattr(X, 'columns', None)
    if blend_weight <= 0 or columns is None or 'rolling_mean_7' not in columns:
        return raw

    baseline = np.nan_to_num(np.asarray(X['rolling_mean_7'], dtype=np.float64) * 7.0, nan=0.0)
    baseline = np.maximum(baseline, 0.0)
    return blend_weight * raw + (1.0 - blend_weight) * baseline
