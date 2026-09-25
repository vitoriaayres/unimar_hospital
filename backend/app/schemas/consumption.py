from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConsumptionBase(BaseModel):
    product_id: UUID
    consumption_date: date
    quantity: int = Field(ge=0)
    department: Literal['icu', 'er', 'ward', 'outpatient']
    prescription_type: Literal['routine', 'emergency', 'prophylactic'] = 'routine'
    context: dict = Field(default_factory=dict)


class ConsumptionCreate(ConsumptionBase):
    pass


class ConsumptionBulkCreate(BaseModel):
    items: list[ConsumptionCreate]


class ConsumptionResponse(ConsumptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ConsumptionListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    product_id: UUID | None = None
    department: Literal['icu', 'er', 'ward', 'outpatient'] | None = None
    prescription_type: Literal['routine', 'emergency', 'prophylactic'] | None = None
    start_date: date | None = None
    end_date: date | None = None
    sort_by: str = Field(default='consumption_date')
    sort_order: Literal['asc', 'desc'] = 'desc'


class ConsumptionListResponse(BaseModel):
    items: list[ConsumptionResponse]
    total: int
    page: int
    size: int
    pages: int


class ConsumptionAggregate(BaseModel):
    period: str
    total_quantity: int
    by_department: dict[str, int]
    by_category: dict[str, int]
    by_prescription_type: dict[str, int]
