from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import (
    Product, InventoryBatch, Consumption, Alert, User, Prediction,
    BatchStatus, AlertType, AlertSeverity, Department
)
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardKPIs,
    StockoutRiskItem,
    ExpiryTimelineItem,
    ConsumptionTrendPoint,
)

router = APIRouter(prefix="/dashboard")


@router.get("/kpis", response_model=DashboardKPIs, summary="Get dashboard KPIs")
async def get_kpis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DashboardKPIs:
    # Total SKUs
    total_skus = await db.scalar(select(func.count(Product.id)).where(Product.is_active == True)) or 0

    # Low stock count
    low_stock_subq = (
        select(func.coalesce(func.sum(InventoryBatch.quantity).filter(InventoryBatch.status == BatchStatus.AVAILABLE), 0))
        .where(and_(InventoryBatch.product_id == Product.id, InventoryBatch.status != BatchStatus.RECALLED))
        .scalar_subquery()
    )
    low_stock_count = await db.scalar(
        select(func.count(Product.id))
        .where(and_(Product.is_active == True, low_stock_subq <= Product.min_stock_level))
    ) or 0

    # Stockout risk count (simplified)
    stockout_risk_count = await db.scalar(
        select(func.count(Alert.id))
        .where(and_(Alert.alert_type == AlertType.SHORTAGE_RISK, Alert.acknowledged == False))
    ) or 0

    # Expiring soon (30 days)
    expiring_soon_count = await db.scalar(
        select(func.count(InventoryBatch.id))
        .where(and_(
            InventoryBatch.status == BatchStatus.AVAILABLE,
            InventoryBatch.expiry_date <= func.current_date() + 30,
            InventoryBatch.expiry_date >= func.current_date(),
        ))
    ) or 0

    # Total inventory value
    total_inventory_value = await db.scalar(
        select(func.coalesce(func.sum(InventoryBatch.quantity * InventoryBatch.unit_cost), 0))
        .where(InventoryBatch.status == BatchStatus.AVAILABLE)
    ) or 0.0

    # Average MAPE
    avg_mape = await db.scalar(
        select(func.avg(Prediction.mape_score))
        .where(Prediction.mape_score.isnot(None))
    ) or 0.0

    # Predictions generated today
    predictions_today = await db.scalar(
        select(func.count(Prediction.id))
        .where(func.date(Prediction.created_at) == func.current_date())
    ) or 0

    # Unacknowledged alerts
    alerts_unacknowledged = await db.scalar(
        select(func.count(Alert.id))
        .where(Alert.acknowledged == False)
    ) or 0

    return DashboardKPIs(
        total_skus=total_skus,
        low_stock_count=low_stock_count,
        stockout_risk_count=stockout_risk_count,
        expiring_soon_count=expiring_soon_count,
        total_inventory_value=float(total_inventory_value),
        average_mape=float(avg_mape),
        predictions_generated_today=predictions_today,
        alerts_unacknowledged=alerts_unacknowledged,
    )


@router.get("/stockout-risk", response_model=list[StockoutRiskItem], summary="Get stockout risk items")
async def get_stockout_risk(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[StockoutRiskItem]:
    # Simplified stockout risk calculation
    query = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
            func.coalesce(func.sum(InventoryBatch.quantity).filter(InventoryBatch.status == BatchStatus.AVAILABLE), 0).label("current_stock"),
            func.coalesce(func.avg(Consumption.quantity), 40).label("daily_avg"),
        )
        .outerjoin(InventoryBatch, and_(Product.id == InventoryBatch.product_id, InventoryBatch.status != BatchStatus.RECALLED))
        .outerjoin(Consumption, and_(Product.id == Consumption.product_id, Consumption.consumption_date >= func.current_date() - 30))
        .where(Product.is_active == True)
        .group_by(Product.id, Product.name, Product.sku, Product.min_stock_level)
        .having(func.coalesce(func.sum(InventoryBatch.quantity).filter(InventoryBatch.status == BatchStatus.AVAILABLE), 0) <= Product.max_stock_level)
        .order_by(func.coalesce(func.sum(InventoryBatch.quantity).filter(InventoryBatch.status == BatchStatus.AVAILABLE), 0).asc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        current_stock = row.current_stock
        daily_avg = float(row.daily_avg) if row.daily_avg else 40.0
        days_until_stockout = int(current_stock / daily_avg) if daily_avg > 0 else None
        
        if days_until_stockout is not None and days_until_stockout <= 3:
            risk_level = "critical"
        elif days_until_stockout is not None and days_until_stockout <= 7:
            risk_level = "high"
        elif days_until_stockout is not None and days_until_stockout <= 14:
            risk_level = "medium"
        else:
            risk_level = "low"

        items.append(StockoutRiskItem(
            product_id=row.product_id,
            product_name=row.product_name,
            product_sku=row.product_sku,
            current_stock=row.current_stock,
            predicted_consumption_7d=int(daily_avg * 7),
            predicted_consumption_30d=int(daily_avg * 30),
            days_until_stockout=days_until_stockout,
            risk_level=risk_level,
            recommended_order_qty=max(0, 100 - row.current_stock),  # Simplified
        ))

    return items


@router.get("/expiry-timeline", response_model=list[ExpiryTimelineItem], summary="Get expiry timeline")
async def get_expiry_timeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days_ahead: int = Query(default=90, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ExpiryTimelineItem]:
    query = (
        select(
            InventoryBatch.id.label("batch_id"),
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
            InventoryBatch.batch_number,
            InventoryBatch.quantity,
            InventoryBatch.expiry_date,
            InventoryBatch.status,
        )
        .join(Product, InventoryBatch.product_id == Product.id)
        .where(and_(
            InventoryBatch.status == BatchStatus.AVAILABLE,
            InventoryBatch.expiry_date <= func.current_date() + days_ahead,
            InventoryBatch.expiry_date >= func.current_date(),
        ))
        .order_by(InventoryBatch.expiry_date.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        days_until = (row.expiry_date - date.today()).days
        items.append(ExpiryTimelineItem(
            batch_id=row.batch_id,
            product_id=row.product_id,
            product_name=row.product_name,
            product_sku=row.product_sku,
            batch_number=row.batch_number,
            quantity=row.quantity,
            expiry_date=row.expiry_date,
            days_until_expiry=days_until,
            status=row.status,
        ))

    return items


@router.get("/consumption-trends", response_model=list[ConsumptionTrendPoint], summary="Get consumption trends")
async def get_consumption_trends(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days_back: int = Query(default=30, ge=1, le=365),
    department: Department | None = None,
) -> list[ConsumptionTrendPoint]:
    from datetime import timedelta
    
    start_date = date.today() - timedelta(days=days_back)
    
    query = (
        select(
            Consumption.consumption_date,
            func.sum(Consumption.quantity).label("total_quantity"),
        )
        .where(and_(
            Consumption.consumption_date >= start_date,
            Consumption.consumption_date <= date.today(),
        ))
    )
    
    if department:
        query = query.where(Consumption.department == department)
    
    query = query.group_by(Consumption.consumption_date).order_by(Consumption.consumption_date.asc())
    
    result = await db.execute(query)
    rows = result.all()

    trends = []
    for row in rows:
        # Get breakdown by department and category
        dept_query = (
            select(Consumption.department, func.sum(Consumption.quantity))
            .where(Consumption.consumption_date == row.consumption_date)
            .group_by(Consumption.department)
        )
        dept_result = await db.execute(dept_query)
        by_dept = {str(r.department): r[1] for r in dept_result.all()}

        cat_query = (
            select(Product.category, func.sum(Consumption.quantity))
            .join(Product, Consumption.product_id == Product.id)
            .where(Consumption.consumption_date == row.consumption_date)
            .group_by(Product.category)
        )
        cat_result = await db.execute(cat_query)
        by_cat = {str(r.category): r[1] for r in cat_result.all()}

        trends.append(ConsumptionTrendPoint(
            date=row.consumption_date,
            total_quantity=row.total_quantity,
            by_department=by_dept,
            by_category=by_cat,
        ))

    return trends


@router.get("", response_model=DashboardResponse, summary="Get full dashboard data")
async def get_dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DashboardResponse:
    from datetime import datetime
    
    kpis = await get_kpis(db, current_user)
    stockout_risks = await get_stockout_risk(db, current_user)
    expiry_timeline = await get_expiry_timeline(db, current_user)
    consumption_trends = await get_consumption_trends(db, current_user)

    return DashboardResponse(
        kpis=kpis,
        stockout_risks=stockout_risks,
        expiry_timeline=expiry_timeline,
        consumption_trends=consumption_trends,
        generated_at=datetime.utcnow().isoformat(),
    )