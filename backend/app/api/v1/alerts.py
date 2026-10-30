from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_manager
from app.models import Alert, User
from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertBulkAcknowledgeRequest,
    AlertListParams,
    AlertListResponse,
    AlertResponse,
    AlertRuleResponse,
    AlertRuleUpdate,
)

router = APIRouter(prefix='/alerts')

_alert_rules = {
    'shortage_risk': {'enabled': True, 'threshold_days': 7, 'severity': 'warning', 'notify_roles': ['pharmacist', 'manager']},
    'expiry_risk': {'enabled': True, 'threshold_days': 90, 'severity': 'warning', 'notify_roles': ['pharmacist', 'manager']},
    'overstock': {'enabled': True, 'threshold_days': 0, 'severity': 'info', 'notify_roles': ['manager']},
    'reorder_point': {'enabled': True, 'threshold_days': 0, 'severity': 'info', 'notify_roles': ['pharmacist']},
}


@router.get('', response_model=AlertListResponse, summary='List alerts (paginated)')
async def list_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[AlertListParams, Depends()],
) -> AlertListResponse:
    query = select(Alert).options(selectinload(Alert.product))

    if params.product_id:
        query = query.where(Alert.product_id == params.product_id)
    if params.alert_type:
        query = query.where(Alert.alert_type == params.alert_type)
    if params.severity:
        query = query.where(Alert.severity == params.severity)
    if params.acknowledged is not None:
        query = query.where(Alert.acknowledged == params.acknowledged)
    if params.start_date:
        query = query.where(Alert.created_at >= params.start_date)
    if params.end_date:
        query = query.where(Alert.created_at <= params.end_date)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    sort_column = getattr(Alert, params.sort_by, Alert.created_at)
    query = query.order_by(sort_column.desc() if params.sort_order == 'desc' else sort_column.asc())
    query = query.offset((params.page - 1) * params.size).limit(params.size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    pages = (total + params.size - 1) // params.size if params.size else 0

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


@router.post('/{alert_id}/acknowledge', response_model=AlertResponse, summary='Acknowledge alert')
async def acknowledge_alert(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    alert_id: UUID,
    ack_data: AlertAcknowledgeRequest,
) -> AlertResponse:
    result = await db.execute(
        select(Alert).options(selectinload(Alert.product)).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, 'Alert not found')

    from datetime import datetime
    if ack_data.acknowledged:
        alert.acknowledged = True
        alert.acknowledged_by = current_user.id
        alert.acknowledged_at = datetime.utcnow()
    else:
        alert.acknowledged = False
        alert.acknowledged_by = None
        alert.acknowledged_at = None

    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post('/bulk-acknowledge', response_model=list[AlertResponse], summary='Bulk acknowledge')
async def bulk_acknowledge_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    bulk_data: AlertBulkAcknowledgeRequest,
) -> list[AlertResponse]:
    result = await db.execute(
        select(Alert).options(selectinload(Alert.product)).where(Alert.id.in_(bulk_data.ids))
    )
    alerts = result.scalars().all()

    from datetime import datetime
    for alert in alerts:
        alert.acknowledged = True
        alert.acknowledged_by = current_user.id
        alert.acknowledged_at = datetime.utcnow()

    await db.commit()
    for alert in alerts:
        await db.refresh(alert)
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get('/rules', response_model=list[AlertRuleResponse], summary='Get alert rules')
async def list_alert_rules(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AlertRuleResponse]:
    return [
        AlertRuleResponse(
            id=alert_type,
            alert_type=alert_type,
            enabled=cfg['enabled'],
            threshold_days=cfg['threshold_days'],
            severity=cfg['severity'],
            notify_roles=cfg['notify_roles'],
            created_at='2024-01-01T00:00:00',
            updated_at='2024-01-01T00:00:00',
        )
        for alert_type, cfg in _alert_rules.items()
    ]


@router.patch('/rules/{rule_id}', response_model=AlertRuleResponse, summary='Update an alert rule')
async def update_alert_rule(
    rule_id: str,
    current_user: Annotated[User, Depends(require_manager)],
    rule_update: AlertRuleUpdate,
) -> AlertRuleResponse:
    cfg = _alert_rules.get(rule_id)
    if cfg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Alert rule not found')

    # Regras ficam em memoria: valem ate o backend reiniciar
    cfg.update(rule_update.model_dump(exclude_unset=True))
    rules = await list_alert_rules(current_user)
    return next(r for r in rules if r.id == rule_id)
