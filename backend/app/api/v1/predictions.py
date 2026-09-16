from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import Prediction, Product, User
from app.schemas.prediction import (
    ForecastRequest,
    ForecastResponse,
    ModelComparison,
    PredictionListParams,
    PredictionListResponse,
    PredictionResponse,
)

router = APIRouter()


@router.get("", response_model=PredictionListResponse, summary="List predictions")
async def list_predictions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[PredictionListParams, Depends()],
) -> PredictionListResponse:
    query = select(Prediction)

    if params.product_id:
        query = query.where(Prediction.product_id == params.product_id)

    if params.model_version:
        query = query.where(Prediction.model_version == params.model_version)

    if params.start_date:
        query = query.where(Prediction.forecast_date >= params.start_date)

    if params.end_date:
        query = query.where(Prediction.forecast_date <= params.end_date)

    # Count total
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Prediction, params.sort_by, Prediction.forecast_date)
    if params.sort_order == "desc":
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


@router.post("/forecast", response_model=ForecastResponse, summary="Generate demand forecast")
async def generate_forecast(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    forecast_request: ForecastRequest,
) -> ForecastResponse:
    # TODO: Implement actual ML inference
    # For now, return mock data
    from datetime import datetime, timedelta
    
    product_result = await db.execute(select(Product).where(Product.id == forecast_request.product_id))
    product = product_result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Mock predictions
    predictions = []
    base_qty = 40
    for i in range(forecast_request.horizon_days):
        pred_date = date.today() + timedelta(days=i+1)
        predictions.append({
            "forecast_date": pred_date,
            "predicted_quantity": base_qty + (i % 5),
            "confidence_lower": base_qty - 5,
            "confidence_upper": base_qty + 10,
        })

    return ForecastResponse(
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        model_version=forecast_request.model_version or "lightgbm-v1",
        horizon_days=forecast_request.horizon_days,
        generated_at=datetime.utcnow(),
        predictions=predictions,
        summary={"avg_daily": base_qty, "total_predicted": base_qty * forecast_request.horizon_days},
    )


@router.get("/models", response_model=list[ModelComparison], summary="List available models")
async def list_models(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ModelComparison]:
    # TODO: Query MLflow for registered models
    return [
        ModelComparison(
            model_version="lightgbm-v1",
            model_type="LightGBM",
            mape=0.124,
            rmse=8.5,
            mae=5.2,
            smape=0.112,
            coverage=0.82,
            interval_width=12.3,
            training_date="2024-01-15T10:00:00",
            is_production=True,
            is_staging=False,
        ),
        ModelComparison(
            model_version="xgboost-v1",
            model_type="XGBoost",
            mape=0.131,
            rmse=9.1,
            mae=5.8,
            smape=0.118,
            coverage=0.80,
            interval_width=13.1,
            training_date="2024-01-15T10:30:00",
            is_production=False,
            is_staging=True,
        ),
    ]