from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardKPIs(BaseModel):
    total_skus: int = Field(ge=0)
    low_stock_count: int = Field(ge=0)
    stockout_risk_count: int = Field(ge=0)
    expiring_soon_count: int = Field(ge=0)
    total_inventory_value: float = Field(ge=0)
    average_mape: float = Field(ge=0, le=1)
    predictions_generated_today: int = Field(ge=0)
    alerts_unacknowledged: int = Field(ge=0)


class StockoutRiskItem(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int = Field(ge=0)
    predicted_consumption_7d: int = Field(ge=0)
    predicted_consumption_30d: int = Field(ge=0)
    days_until_stockout: int | None = Field(default=None, ge=0)
    risk_level: Literal['low', 'medium', 'high', 'critical']
    recommended_order_qty: int = Field(ge=0)


class ExpiryTimelineItem(BaseModel):
    batch_id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    batch_number: str
    quantity: int = Field(ge=0)
    expiry_date: date
    days_until_expiry: int = Field(ge=0)
    status: Literal['available', 'reserved', 'expired', 'recalled', 'quarantine']


class ConsumptionTrendPoint(BaseModel):
    date: date
    total_quantity: int = Field(ge=0)
    by_department: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)


class DashboardResponse(BaseModel):
    kpis: DashboardKPIs
    stockout_risks: list[StockoutRiskItem]
    expiry_timeline: list[ExpiryTimelineItem]
    consumption_trends: list[ConsumptionTrendPoint]
    generated_at: str