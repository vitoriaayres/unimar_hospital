from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventoryBatchBase(BaseModel):
    batch_number: str = Field(min_length=1, max_length=50)
    quantity: int = Field(ge=0)
    expiry_date: date
    manufacture_date: date | None = None
    unit_cost: Decimal = Field(default=Decimal('0.00'), ge=0, decimal_places=2)


class InventoryBatchCreate(InventoryBatchBase):
    product_id: UUID
    warehouse_id: UUID


class InventoryBatchUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    expiry_date: date | None = None
    manufacture_date: date | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    status: Literal['available', 'reserved', 'expired', 'recalled', 'quarantine'] | None = None


class InventoryBatchResponse(InventoryBatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    status: Literal['available', 'reserved', 'expired', 'recalled', 'quarantine']
    received_at: datetime
    created_at: datetime
    updated_at: datetime
    days_until_expiry: int | None = None
    is_expired: bool = False
    is_expiring_soon: bool = False


class StockMovementBase(BaseModel):
    quantity_change: int
    movement_type: Literal['in', 'out', 'adjustment', 'transfer', 'loss', 'expired', 'recalled']
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: UUID | None = None
    notes: str | None = None


class StockMovementCreate(StockMovementBase):
    batch_id: UUID


class StockMovementResponse(StockMovementBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    user_id: UUID | None
    created_at: datetime


class InventorySummary(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    total_quantity: int
    available_quantity: int
    reserved_quantity: int
    expired_quantity: int
    batches_count: int
    batches_expiring_30d: int
    batches_expiring_90d: int
    total_value: Decimal
    min_stock_level: int
    max_stock_level: int
    days_of_supply: float | None
    is_low_stock: bool
    is_overstock: bool
