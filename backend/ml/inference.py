"""Inferencia em producao.

O alvo do modelo e a soma do consumo dos proximos 7 dias, treinado em escala
log1p. A predicao final combina o modelo com um baseline de media movel de 7
dias, que reduz a variancia em produtos de baixo volume.
"""

from __future__ import annotations

import numpy as np

# Peso do modelo na combinacao (otimizado na validacao temporal, ver ml/train.py)
BLEND_WEIGHT = 0.5


def predict_demand(model, X, blend_weight: float = BLEND_WEIGHT) -> np.ndarray:
    """Retorna a previsao de consumo total dos proximos 7 dias."""
    raw = np.maximum(np.expm1(model.predict(X)), 0.0)

    columns = getattr(X, 'columns', None)
    if blend_weight <= 0 or columns is None or 'rolling_mean_7' not in columns:
        return raw

    baseline = np.nan_to_num(np.asarray(X['rolling_mean_7'], dtype=np.float64) * 7.0, nan=0.0)
    baseline = np.maximum(baseline, 0.0)
    return blend_weight * raw + (1.0 - blend_weight) * baseline
