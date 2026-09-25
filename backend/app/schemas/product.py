from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    generic_name: str | None = Field(default=None, max_length=255)
    category: Literal[
        'antibiotic',
        'analgesic',
        'antithrombotic',
        'beta_blocker',
        'ppi',
        'bronchodilator',
        'psycholeptic',
        'ace_inhibitor',
        'corticosteroid',
        'other',
    ] = 'other'
    atc_code: str | None = Field(default=None, max_length=20)
    unit: str = Field(default='un', max_length=20)
    unit_cost: Decimal = Field(default=Decimal('0.00'), ge=0, decimal_places=2)
    min_stock_level: int = Field(default=0, ge=0)
    max_stock_level: int = Field(default=100, ge=0)
    lead_time_days: int = Field(default=7, ge=0)
    controlled_substance: bool = False

    @field_validator('unit_cost', mode='before')
    @classmethod
    def _quantize_unit_cost(cls, value: object) -> object:
        if value is None:
            return value
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    generic_name: str | None = Field(default=None, max_length=255)
    category: (
        Literal[
            'antibiotic',
            'analgesic',
            'antithrombotic',
            'beta_blocker',
            'ppi',
            'bronchodilator',
            'psycholeptic',
            'ace_inhibitor',
            'corticosteroid',
            'other',
        ]
        | None
    ) = None
    atc_code: str | None = Field(default=None, max_length=20)
    unit: str | None = Field(default=None, max_length=20)
    unit_cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    min_stock_level: int | None = Field(default=None, ge=0)
    max_stock_level: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)
    controlled_substance: bool | None = None
    is_active: bool | None = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    metadata: dict = Field(alias='product_metadata')
    created_at: datetime
    updated_at: datetime


class ProductListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    search: str | None = None
    category: str | None = None
    controlled_substance: bool | None = None
    is_active: bool | None = True
    sort_by: str = Field(default='name')
    sort_order: Literal['asc', 'desc'] = 'asc'


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    size: int
    pages: int
