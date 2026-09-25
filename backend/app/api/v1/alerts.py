from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_manager
from app.models import Alert, User
from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertBulkAcknowledgeRequest,
    AlertListParams,
    AlertResponse,
    AlertRuleResponse,
    AlertRuleUpdate,
)

router = APIRouter(prefix='/alerts')


# Mock alert rules storage (in production, this would be in DB)
_alert_rules = {
    'shortage_risk': {
        'enabled': True,
        'threshold_days': 7,
        'severity': 'warning',
        'notify_roles': ['pharmacist', 'manager'],
    },
    'expiry_risk': {
        'enabled': True,
        'threshold_days': 90,
        'severity': 'warning',
        'notify_roles': ['pharmacist', 'manager'],
    },
    'overstock': {
        'enabled': True,
        'threshold_days': 0,
        'severity': 'info',
        'notify_roles': ['manager'],
    },
    'reorder_point': {
        'enabled': True,
        'threshold_days': 0,
        'severity': 'info',
        'notify_roles': ['pharmacist'],
    },
}


@router.get('', response_model=list[AlertResponse], summary='List alerts')
async def list_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[AlertListParams, Depends()],
) -> list[AlertResponse]:
    query = select(Alert)

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

    # Apply sorting
    sort_column = getattr(Alert, params.sort_by, Alert.created_at)
    if params.sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    query = query.offset((params.page - 1) * params.size).limit(params.size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return [AlertResponse.model_validate(a) for a in alerts]


@router.post('/{alert_id}/acknowledge', response_model=AlertResponse, summary='Acknowledge alert')
async def acknowledge_alert(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    alert_id: UUID,
    ack_data: AlertAcknowledgeRequest,
) -> AlertResponse:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Alert not found',
        )

    if ack_data.acknowledged:
        alert.acknowledged = True
        alert.acknowledged_by = current_user.id
        from datetime import datetime

        alert.acknowledged_at = datetime.utcnow()
    else:
        alert.acknowledged = False
        alert.acknowledged_by = None
        alert.acknowledged_at = None

    await db.commit()
    await db.refresh(alert)

    return AlertResponse.model_validate(alert)


@router.post(
    '/bulk-acknowledge', response_model=list[AlertResponse], summary='Bulk acknowledge alerts'
)
async def bulk_acknowledge_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    bulk_data: AlertBulkAcknowledgeRequest,
) -> list[AlertResponse]:
    result = await db.execute(select(Alert).where(Alert.id.in_(bulk_data.ids)))
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
    rules = []
    for alert_type, config in _alert_rules.items():
        rules.append(
            AlertRuleResponse(
                id=alert_type,
                alert_type=alert_type,
                enabled=config['enabled'],
                threshold_days=config['threshold_days'],
                severity=config['severity'],
                notify_roles=config['notify_roles'],
                created_at='2024-01-01T00:00:00',
                updated_at='2024-01-01T00:00:00',
            )
        )
    return rules


@router.patch('/rules', response_model=list[AlertRuleResponse], summary='Update alert rules')
async def update_alert_rules(
    current_user: Annotated[User, Depends(require_manager)],
    rules_update: AlertRuleUpdate,
) -> list[AlertRuleResponse]:
    # In production, this would update the database
    # For now, just return the current rules
    rules = []
    for alert_type, config in _alert_rules.items():
        rules.append(
            AlertRuleResponse(
                id=alert_type,
                alert_type=alert_type,
                enabled=config['enabled'],
                threshold_days=config['threshold_days'],
                severity=config['severity'],
                notify_roles=config['notify_roles'],
                created_at='2024-01-01T00:00:00',
                updated_at='2024-01-01T00:00:00',
            )
        )
    return rules
