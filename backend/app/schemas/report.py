from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    report_type: Literal[
        'stock_position',
        'expiry_analysis',
        'consumption_trends',
        'forecast_accuracy',
        'alert_summary',
        'custom',
    ]
    format: Literal['pdf', 'excel'] = 'pdf'
    filters: dict = Field(default_factory=dict)
    schedule_cron: str | None = Field(
        default=None,
        pattern=r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])|\*/[0-9]+) (\*|([0-9]|1[0-9]|2[0-3])|\*/[0-9]+) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])|\*/[0-9]+) (\*|([1-9]|1[0-2])|\*/[0-9]+) (\*|([0-6])|\*/[0-9]+)$',
    )


class ReportCreate(ReportBase):
    pass


class ReportUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    report_type: (
        Literal[
            'stock_position',
            'expiry_analysis',
            'consumption_trends',
            'forecast_accuracy',
            'alert_summary',
            'custom',
        ]
        | None
    ) = None
    format: Literal['pdf', 'excel'] | None = None
    filters: dict | None = None
    schedule_cron: str | None = Field(
        default=None,
        pattern=r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])|\*/[0-9]+) (\*|([0-9]|1[0-9]|2[0-3])|\*/[0-9]+) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])|\*/[0-9]+) (\*|([1-9]|1[0-2])|\*/[0-9]+) (\*|([0-6])|\*/[0-9]+)$',
    )
    is_active: bool | None = None


class ReportResponse(ReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    last_generated_at: datetime | None
    next_scheduled_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class ReportExecutionResponse(BaseModel):
    id: UUID
    report_id: UUID
    status: Literal['pending', 'running', 'completed', 'failed']
    file_path: str | None = None
    file_size: int | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
