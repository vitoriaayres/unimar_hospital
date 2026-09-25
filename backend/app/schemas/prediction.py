from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PredictionPoint(BaseModel):
    forecast_date: date
    predicted_quantity: int = Field(ge=0)
    confidence_lower: int = Field(ge=0)
    confidence_upper: int = Field(ge=0)


class PredictionBase(BaseModel):
    product_id: UUID
    forecast_date: date
    predicted_quantity: int = Field(ge=0)
    confidence_lower: int = Field(ge=0)
    confidence_upper: int = Field(ge=0)
    model_version: str = Field(min_length=1, max_length=100)
    mape_score: float | None = Field(default=None, ge=0, le=1)
    wape_score: float | None = Field(default=None, ge=0, le=1)


class PredictionCreate(PredictionBase):
    pass


class PredictionResponse(PredictionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class PredictionListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    product_id: UUID | None = None
    model_version: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    sort_by: str = Field(default='forecast_date')
    sort_order: Literal['asc', 'desc'] = 'desc'


class PredictionListResponse(BaseModel):
    items: list[PredictionResponse]
    total: int
    page: int
    size: int
    pages: int


class ForecastRequest(BaseModel):
    product_id: UUID
    horizon_days: int = Field(default=30, ge=1, le=90)
    model_version: str | None = None


class ForecastResponse(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    model_version: str
    horizon_days: int
    generated_at: datetime
    predictions: list[PredictionPoint]
    summary: dict


class ModelComparison(BaseModel):
    model_version: str
    model_type: str
    wape: float
    mape: float
    rmse: float
    mae: float
    smape: float
    coverage: float
    interval_width: float
    training_date: datetime
    is_production: bool
    is_staging: bool
