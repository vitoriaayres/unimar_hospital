from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertBase(BaseModel):
    product_id: UUID
    alert_type: Literal['shortage_risk', 'expiry_risk', 'overstock', 'reorder_point']
    severity: Literal['info', 'warning', 'critical']
    message: str
    metadata: dict = Field(default_factory=dict, alias="alert_metadata")


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    acknowledged: bool
    acknowledged_by: UUID | None
    acknowledged_at: datetime | None
    created_at: datetime


class AlertAcknowledgeRequest(BaseModel):
    acknowledged: bool = True


class AlertBulkAcknowledgeRequest(BaseModel):
    ids: list[UUID]


class AlertListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    product_id: UUID | None = None
    alert_type: Literal['shortage_risk', 'expiry_risk', 'overstock', 'reorder_point'] | None = None
    severity: Literal['info', 'warning', 'critical'] | None = None
    acknowledged: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    sort_by: str = Field(default='created_at')
    sort_order: Literal['asc', 'desc'] = 'desc'


class AlertRuleBase(BaseModel):
    alert_type: Literal['shortage_risk', 'expiry_risk', 'overstock', 'reorder_point']
    enabled: bool = True
    threshold_days: int = Field(default=7, ge=1, le=90)
    severity: Literal['info', 'warning', 'critical'] = 'warning'
    notify_roles: list[Literal['pharmacist', 'manager', 'admin']] = Field(default_factory=list)


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None
    threshold_days: int | None = Field(default=None, ge=1, le=90)
    severity: Literal['info', 'warning', 'critical'] | None = None
    notify_roles: list[Literal['pharmacist', 'manager', 'admin']] | None = None


class AlertRuleResponse(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime