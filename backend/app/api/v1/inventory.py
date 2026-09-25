from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import (
    BatchStatus,
    InventoryBatch,
    MovementType,
    Product,
    StockMovement,
    User,
    UserRole,
)
from app.schemas.inventory import (
    InventoryBatchCreate,
    InventoryBatchResponse,
    InventoryBatchUpdate,
    InventorySummary,
    StockMovementCreate,
    StockMovementResponse,
)

router = APIRouter(prefix='/inventory')


def _check_manager_or_admin(user: User) -> None:
    if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only managers and administrators can perform this action',
        )


@router.get(
    '/summary',
    response_model=list[InventorySummary],
    summary='Get inventory summary for all products',
)
async def get_inventory_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    low_stock_only: bool = Query(default=False, description='Show only low stock items'),
    expiring_days: int = Query(default=90, ge=1, le=365, description='Days until expiry to flag'),
) -> list[InventorySummary]:
    # Get all active products with their batch aggregates
    query = (
        select(
            Product.id.label('product_id'),
            Product.name.label('product_name'),
            Product.sku.label('product_sku'),
            Product.min_stock_level,
            Product.max_stock_level,
            func.coalesce(func.sum(InventoryBatch.quantity), 0).label('total_quantity'),
            func.coalesce(
                func.sum(InventoryBatch.quantity).filter(
                    InventoryBatch.status == BatchStatus.AVAILABLE
                ),
                0,
            ).label('available_quantity'),
            func.coalesce(
                func.sum(InventoryBatch.quantity).filter(
                    InventoryBatch.status == BatchStatus.RESERVED
                ),
                0,
            ).label('reserved_quantity'),
            func.coalesce(
                func.sum(InventoryBatch.quantity).filter(
                    InventoryBatch.status == BatchStatus.EXPIRED
                ),
                0,
            ).label('expired_quantity'),
            func.count(InventoryBatch.id).label('batches_count'),
            func.count(InventoryBatch.id)
            .filter(
                and_(
                    InventoryBatch.expiry_date <= func.current_date() + expiring_days,
                    InventoryBatch.expiry_date >= func.current_date(),
                    InventoryBatch.status == BatchStatus.AVAILABLE,
                )
            )
            .label('batches_expiring_30d'),
            func.count(InventoryBatch.id)
            .filter(
                and_(
                    InventoryBatch.expiry_date <= func.current_date() + expiring_days,
                    InventoryBatch.expiry_date >= func.current_date(),
                    InventoryBatch.status == BatchStatus.AVAILABLE,
                )
            )
            .label('batches_expiring_90d'),
            func.coalesce(func.sum(InventoryBatch.quantity * InventoryBatch.unit_cost), 0).label(
                'total_value'
            ),
        )
        .outerjoin(
            InventoryBatch,
            and_(
                Product.id == InventoryBatch.product_id,
                InventoryBatch.status != BatchStatus.RECALLED,
            ),
        )
        .where(Product.is_active.is_(True))
        .group_by(
            Product.id, Product.name, Product.sku, Product.min_stock_level, Product.max_stock_level
        )
    )

    result = await db.execute(query)
    rows = result.all()

    summaries = []
    for row in rows:
        total_qty = row.total_quantity
        available_qty = row.available_quantity
        min_level = row.min_stock_level
        max_level = row.max_stock_level

        is_low_stock = available_qty <= min_level
        is_overstock = available_qty >= max_level

        if low_stock_only and not is_low_stock:
            continue

        days_of_supply = None
        if total_qty > 0 and row.total_value is not None:
            # This would need consumption data to calculate properly
            pass

        summaries.append(
            InventorySummary(
                product_id=row.product_id,
                product_name=row.product_name,
                product_sku=row.product_sku,
                total_quantity=total_qty,
                available_quantity=available_qty,
                reserved_quantity=row.reserved_quantity,
                expired_quantity=row.expired_quantity,
                batches_count=row.batches_count,
                batches_expiring_30d=row.batches_expiring_30d or 0,
                batches_expiring_90d=row.batches_expiring_90d or 0,
                total_value=row.total_value or 0,
                min_stock_level=min_level,
                max_stock_level=max_level,
                days_of_supply=days_of_supply,
                is_low_stock=is_low_stock,
                is_overstock=is_overstock,
            )
        )

    return summaries


@router.get(
    '/batches', response_model=list[InventoryBatchResponse], summary='List inventory batches'
)
async def list_batches(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    product_id: UUID | None = None,
    status: BatchStatus | None = None,
    expiring_within_days: int | None = Query(default=None, ge=1, le=365),
    skip: int = 0,
    limit: int = 100,
) -> list[InventoryBatchResponse]:
    query = select(InventoryBatch).where(InventoryBatch.status != BatchStatus.RECALLED)

    if product_id:
        query = query.where(InventoryBatch.product_id == product_id)

    if status:
        query = query.where(InventoryBatch.status == status)

    if expiring_within_days:
        from datetime import date, timedelta

        expiry_limit = date.today() + timedelta(days=expiring_within_days)
        query = query.where(
            and_(
                InventoryBatch.expiry_date <= expiry_limit,
                InventoryBatch.expiry_date >= date.today(),
            )
        )

    query = query.order_by(InventoryBatch.expiry_date.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    batches = result.scalars().all()

    return [InventoryBatchResponse.model_validate(b) for b in batches]


@router.post(
    '/batches',
    response_model=InventoryBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create new inventory batch',
)
async def create_batch(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    batch_data: InventoryBatchCreate,
) -> InventoryBatchResponse:
    _check_manager_or_admin(current_user)

    # Verify product exists
    product_result = await db.execute(select(Product).where(Product.id == batch_data.product_id))
    if not product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found',
        )

    batch = InventoryBatch(**batch_data.model_dump())
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    return InventoryBatchResponse.model_validate(batch)


@router.get('/batches/{batch_id}', response_model=InventoryBatchResponse, summary='Get batch by ID')
async def get_batch(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    batch_id: UUID,
) -> InventoryBatchResponse:
    result = await db.execute(select(InventoryBatch).where(InventoryBatch.id == batch_id))
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Batch not found',
        )

    return InventoryBatchResponse.model_validate(batch)


@router.patch('/batches/{batch_id}', response_model=InventoryBatchResponse, summary='Update batch')
async def update_batch(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    batch_id: UUID,
    batch_data: InventoryBatchUpdate,
) -> InventoryBatchResponse:
    _check_manager_or_admin(current_user)

    result = await db.execute(select(InventoryBatch).where(InventoryBatch.id == batch_id))
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Batch not found',
        )

    update_data = batch_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(batch, field, value)

    await db.commit()
    await db.refresh(batch)

    return InventoryBatchResponse.model_validate(batch)


@router.post(
    '/movements',
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Record stock movement',
)
async def create_movement(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    movement_data: StockMovementCreate,
) -> StockMovementResponse:
    result = await db.execute(
        select(InventoryBatch).where(InventoryBatch.id == movement_data.batch_id)
    )
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Batch not found',
        )

    # Validate movement
    if movement_data.movement_type in (MovementType.OUT, MovementType.TRANSFER, MovementType.LOSS):
        if batch.quantity + movement_data.quantity_change < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Insufficient stock for this movement',
            )

    movement = StockMovement(
        **movement_data.model_dump(),
        user_id=current_user.id,
    )

    # Update batch quantity
    batch.quantity += movement_data.quantity_change

    # Auto-update status
    from datetime import date

    if batch.quantity == 0:
        batch.status = (
            BatchStatus.EXPIRED if batch.expiry_date < date.today() else BatchStatus.AVAILABLE
        )
    elif batch.expiry_date < date.today():
        batch.status = BatchStatus.EXPIRED

    db.add(movement)
    await db.commit()
    await db.refresh(movement)

    return StockMovementResponse.model_validate(movement)


@router.get(
    '/movements', response_model=list[StockMovementResponse], summary='List stock movements'
)
async def list_movements(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    batch_id: UUID | None = None,
    movement_type: MovementType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[StockMovementResponse]:
    query = select(StockMovement).order_by(StockMovement.created_at.desc())

    if batch_id:
        query = query.where(StockMovement.batch_id == batch_id)

    if movement_type:
        query = query.where(StockMovement.movement_type == movement_type)

    if start_date:
        query = query.where(StockMovement.created_at >= start_date)

    if end_date:
        query = query.where(StockMovement.created_at <= end_date)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    movements = result.scalars().all()

    return [StockMovementResponse.model_validate(m) for m in movements]
