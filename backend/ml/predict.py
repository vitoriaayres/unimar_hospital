"""Serviço de previsão de demanda.

Carrega modelo treinado e gera previsões para produtos.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

# Adicionar diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl
import psycopg2

from ml.features import (
    build_features,
    load_consumption,
    load_inventory,
    load_products,
)
from ml.inference import BLEND_WEIGHT, predict_demand

MODEL_DIR = Path('ml/models')
DATA_DIR = Path('ml/data')

DB_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://pharmapredict:pharmapredict_dev@localhost:5432/pharmapredict',
)


def load_blend_weight() -> float:
    """Le o peso do blend otimizado no treino (fallback: padrao)."""
    metrics_path = DATA_DIR / 'metrics_production.json'
    if metrics_path.exists():
        with open(metrics_path, encoding='utf-8') as f:
            weight = json.load(f).get('blend_weight')
        if isinstance(weight, (int, float)):
            return float(weight)
    return BLEND_WEIGHT


def load_production_model():
    """Carrega modelo e lista de features de produção."""
    model_path = MODEL_DIR / 'model_production.pkl'
    features_path = DATA_DIR / 'features_production.json'

    if not model_path.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado: {model_path}\nExecute 'uv run python ml/train.py' primeiro."
        )

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    with open(features_path, encoding='utf-8') as f:
        feature_cols = json.load(f)

    return model, feature_cols


def predict_all(
    model, feature_cols: list[str], features: pl.DataFrame, blend_weight: float = BLEND_WEIGHT
) -> pl.DataFrame:
    """Gera previsão para todos os produtos (último dia disponível)."""
    latest = features.sort('consumption_date', descending=True).group_by('product_id').first()

    X = latest.select(feature_cols).to_pandas()
    preds = predict_demand(model, X, blend_weight)

    result = latest.select(
        [
            'product_id',
            'consumption_date',
            'daily_consumption',
        ]
    ).with_columns(pl.Series('predicted_consumption_7d', preds))

    return result


def predict_single(
    model, feature_cols: list[str], features: pl.DataFrame, product_id: str
) -> dict | None:
    """Gera previsão para um produto específico."""
    product_data = features.filter(pl.col('product_id') == product_id)

    if product_data.is_empty():
        return None

    last_row = product_data.sort('consumption_date', descending=True).head(1)
    X = last_row.select(feature_cols).to_pandas()
    pred = float(predict_demand(model, X, load_blend_weight())[0])

    return {
        'product_id': product_id,
        'current_consumption': float(last_row['daily_consumption'][0]),
        'predicted_consumption_7d': max(0, pred),
        'generated_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
    }


def save_predictions(predictions: pl.DataFrame) -> Path:
    """Salva previsões em Parquet."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / 'predictions.parquet'
    predictions.write_parquet(out_path)
    return out_path


def save_predictions_to_db(
    predictions: pl.DataFrame, model_version: str, mape_score: float, wape_score: float
) -> int:
    """Salva previsoes na tabela predictions do PostgreSQL."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    today = date.today()
    now = datetime.now()

    rows = list(predictions.iter_rows(named=True))
    product_ids = [row['product_id'] for row in rows]

    # Remove previsoes anteriores dos mesmos produtos (evita duplicatas entre
    # versoes do modelo - a tabela guarda apenas a previsao vigente)
    cur.execute(
        'DELETE FROM predictions WHERE product_id::text = ANY(%s)',
        (product_ids,),
    )
    deleted = cur.rowcount

    inserted = 0
    for row in rows:
        product_id = row['product_id']
        pred_7d = max(0, int(round(row['predicted_consumption_7d'])))

        # Confidence interval: +/- 30% do predicted (heuristica simples)
        conf_lower = max(0, int(round(pred_7d * 0.7)))
        conf_upper = int(round(pred_7d * 1.3))

        cur.execute(
            """
            INSERT INTO predictions
                (id, product_id, forecast_date, predicted_quantity,
                 confidence_lower, confidence_upper, model_version, mape_score,
                 wape_score, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                product_id,
                today,
                pred_7d,
                conf_lower,
                conf_upper,
                model_version,
                mape_score,
                wape_score,
                now,
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    if deleted:
        print(f'   Removidas {deleted} previsoes anteriores')
    return inserted


def main() -> None:
    print('=== Servico de Previsao ===\n')

    print('1. Carregando modelo de producao...')
    model, feature_cols = load_production_model()
    print(f'   Features: {len(feature_cols)}')

    # Carregar metricas do modelo
    metrics_path = DATA_DIR / 'metrics_production.json'
    blend_weight = BLEND_WEIGHT
    if metrics_path.exists():
        with open(metrics_path, encoding='utf-8') as f:
            model_metrics = json.load(f)
        model_version = model_metrics.get('trained_at', 'unknown')
        mape_score = model_metrics.get('mape', 0.0)
        wape_score = model_metrics.get('wape', 0.0)
        if isinstance(model_metrics.get('blend_weight'), (int, float)):
            blend_weight = float(model_metrics['blend_weight'])
    else:
        model_version = 'v1.0'
        mape_score = 0.0
        wape_score = 0.0
    print(f'   Blend (peso do modelo): {blend_weight:.2f}')

    print('\n2. Carregando dados...')
    consumption = load_consumption()
    products = load_products()
    inventory = load_inventory()

    print('\n3. Construindo features...')
    features = build_features(consumption, products, inventory)

    print('\n4. Gerando previsoes...')
    predictions = predict_all(model, feature_cols, features, blend_weight)

    print('\n5. Salvando previsoes em Parquet...')
    out_path = save_predictions(predictions)
    print(f'   Salvo: {out_path}')

    print('\n6. Salvando previsoes no banco de dados...')
    try:
        inserted = save_predictions_to_db(predictions, model_version, mape_score, wape_score)
        print(f'   Inseridos: {inserted} registros na tabela predictions')
    except Exception as e:
        print(f'   Erro ao salvar no banco: {e}')

    preds_pandas = predictions.to_pandas()
    print('\n=== Estatisticas ===')
    print(f'   Produtos previstos: {len(preds_pandas)}')
    base_date = preds_pandas['consumption_date'].max()
    print(f'   Janela prevista: D+1 a D+7 a partir de {base_date}')
    print(f'   Media 7d:    {preds_pandas["predicted_consumption_7d"].mean():.1f}')
    print(f'   Mediana 7d:  {preds_pandas["predicted_consumption_7d"].median():.1f}')
    print(f'   Maximo 7d:   {preds_pandas["predicted_consumption_7d"].max():.1f}')
    print(f'   Minimo 7d:   {preds_pandas["predicted_consumption_7d"].min():.1f}')

    print('\n=== Top 10 Maior Demanda Prevista ===')
    top10 = preds_pandas.nlargest(10, 'predicted_consumption_7d')
    for _, row in top10.iterrows():
        print(
            f'   {row["product_id"][:8]}...  consumoAtual={row["daily_consumption"]:>6.0f}  prev7d={row["predicted_consumption_7d"]:>8.1f}'
        )

    print('\n=== Previsao Concluida ===')


if __name__ == '__main__':
    main()
