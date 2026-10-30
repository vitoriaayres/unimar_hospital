from __future__ import annotations

import json
import pickle
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models import Prediction, Product, User
from app.schemas.prediction import (
    ForecastRequest,
    ForecastResponse,
    ModelComparison,
    ModelReport,
    PredictionListParams,
    PredictionListResponse,
    PredictionResponse,
)

router = APIRouter(prefix='/predictions')

MODEL_DIR = Path('ml/models')
DATA_DIR = Path('ml/data')

def _load_production_model():
    model_path = MODEL_DIR / 'model_production.pkl'
    features_path = DATA_DIR / 'features_production.json'

    if not model_path.exists() or not features_path.exists():
        return None, None

    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(features_path) as f:
        feature_cols = json.load(f)
    return model, feature_cols

def _load_production_metrics() -> dict | None:
    """Carrega métricas de produção."""
    metrics_path = DATA_DIR / 'metrics_production.json'
    if not metrics_path.exists():
        return None
    with open(metrics_path) as f:
        return json.load(f)


def _load_model_report() -> dict | None:
    """Carrega o relatório do modelo gerado por ml/train.py."""
    report_path = DATA_DIR / 'model_report_production.json'
    if not report_path.exists():
        return None
    with open(report_path, encoding='utf-8') as f:
        return json.load(f)


def _load_cached_predictions() -> pl.DataFrame | None:
    """Carrega previsões cacheadas."""
    preds_path = DATA_DIR / 'predictions.parquet'
    if not preds_path.exists():
        return None
    return pl.read_parquet(preds_path)


@router.get('', response_model=PredictionListResponse, summary='List predictions')
async def list_predictions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[PredictionListParams, Depends()],
) -> PredictionListResponse:
    query = select(Prediction).options(selectinload(Prediction.product))

    if params.product_id:
        query = query.where(Prediction.product_id == params.product_id)

    if params.search:
        pattern = f'%{params.search}%'
        query = query.join(Product, Prediction.product_id == Product.id).where(
            or_(Product.name.ilike(pattern), Product.sku.ilike(pattern))
        )

    if params.model_version:
        query = query.where(Prediction.model_version == params.model_version)

    if params.start_date:
        query = query.where(Prediction.forecast_date >= params.start_date)

    if params.end_date:
        query = query.where(Prediction.forecast_date <= params.end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Prediction, params.sort_by, Prediction.forecast_date)
    if params.sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    query = query.offset((params.page - 1) * params.size).limit(params.size)
    result = await db.execute(query)
    predictions = result.scalars().all()

    pages = (total + params.size - 1) // params.size

    return PredictionListResponse(
        items=[PredictionResponse.model_validate(p) for p in predictions],
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )

@router.post('/forecast', response_model=ForecastResponse, summary='Generate demand forecast')
async def generate_forecast(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    forecast_request: ForecastRequest,
) -> ForecastResponse:
    product_result = await db.execute(
        select(Product).where(Product.id == forecast_request.product_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Product not found')

    model, _feature_cols = _load_production_model()
    if model is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Modelo ML não treinado. Rode 'uv run python ml/train.py' primeiro.",
        )

    preds_df = _load_cached_predictions()
    if preds_df is None or preds_df.is_empty():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Cache de previsões ausente. Rode 'uv run python ml/predict.py'.",
        )

    product_pred = preds_df.filter(
        pl.col('product_id') == str(forecast_request.product_id)
    )
    if product_pred.is_empty():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            'Sem previsão cacheada para este produto.',
        )

    # O modelo prevê a soma dos próximos 7 dias (target_7d).
    weekly_total = float(product_pred['predicted_consumption_7d'][0])
    daily_avg = max(0.0, weekly_total / 7.0)

    # Heurística de IC: ±20% do valor esperado.
    predictions: list[dict] = []
    for i in range(forecast_request.horizon_days):
        pred_date = date.today() + timedelta(days=i + 1)
        daily_pred = max(0, int(round(daily_avg)))
        conf_range = max(2, int(round(daily_avg * 0.2)))
        predictions.append({
            'forecast_date': pred_date,
            'predicted_quantity': daily_pred,
            'confidence_lower': max(0, daily_pred - conf_range),
            'confidence_upper': daily_pred + conf_range,
        })

    metrics = _load_production_metrics() or {}
    model_version = str(metrics.get('trained_at', 'lightgbm-v1'))
    total_predicted = sum(p['predicted_quantity'] for p in predictions)

    return ForecastResponse(
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        model_version=model_version,
        horizon_days=forecast_request.horizon_days,
        generated_at=datetime.utcnow(),
        predictions=predictions,
        summary={
            'avg_daily': round(daily_avg, 1),
            'total_predicted': total_predicted,
            'wape': metrics.get('wape'),
            'mape': metrics.get('mape'),
        },
    )

@router.get('/model-report', response_model=ModelReport, summary='Model evaluation report')
async def get_model_report(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ModelReport:
    report = _load_model_report()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Relatório do modelo não encontrado. Rode ml/run_pipeline.py.',
        )
    return ModelReport(**report)


@router.get('/models', response_model=list[ModelComparison], summary='List available models')
async def list_models(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ModelComparison]:
    metrics = _load_production_metrics()

    if metrics:
        return [
            ModelComparison(
                model_version='lightgbm-v1',
                model_type='LightGBM',
                wape=metrics.get('wape', 0.0),
                mape=metrics.get('mape', 0.0),
                rmse=metrics.get('rmse', 0.0),
                mae=metrics.get('mae', 0.0),
                smape=metrics.get('smape', 0.0),
                coverage=0.82,
                interval_width=12.3,
                training_date=metrics.get('trained_at', '2024-01-15T10:00:00'),
                is_production=True,
                is_staging=False,
            ),
        ]

    return [
        ModelComparison(
            model_version='lightgbm-v1',
            model_type='LightGBM',
            wape=0.0,
            mape=0.0,
            rmse=0.0,
            mae=0.0,
            smape=0.0,
            coverage=0.0,
            interval_width=0.0,
            training_date='2024-01-15T10:00:00',
            is_production=False,
            is_staging=False,
        ),
    ]
