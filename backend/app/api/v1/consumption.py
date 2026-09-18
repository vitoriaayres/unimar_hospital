from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_manager
from app.models import Consumption, Product, User, Department, PrescriptionType
from app.schemas.consumption import (
    ConsumptionBase,
    ConsumptionBulkCreate,
    ConsumptionListParams,
    ConsumptionListResponse,
    ConsumptionResponse,
)

router = APIRouter(prefix="/consumption")


@router.get("", response_model=ConsumptionListResponse, summary="List consumption records")
async def list_consumption(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[ConsumptionListParams, Depends()],
) -> ConsumptionListResponse:
    query = select(Consumption)

    if params.product_id:
        query = query.where(Consumption.product_id == params.product_id)

    if params.department:
        query = query.where(Consumption.department == params.department)

    if params.prescription_type:
        query = query.where(Consumption.prescription_type == params.prescription_type)

    if params.start_date:
        query = query.where(Consumption.consumption_date >= params.start_date)

    if params.end_date:
        query = query.where(Consumption.consumption_date <= params.end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Consumption, params.sort_by, Consumption.consumption_date)
    if params.sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    query = query.offset((params.page - 1) * params.size).limit(params.size)
    result = await db.execute(query)
    consumptions = result.scalars().all()

    pages = (total + params.size - 1) // params.size

    return ConsumptionListResponse(
        items=[ConsumptionResponse.model_validate(c) for c in consumptions],
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


@router.post("", response_model=ConsumptionResponse, status_code=status.HTTP_201_CREATED, summary="Create consumption record")
async def create_consumption(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    consumption_data: ConsumptionBase,
) -> ConsumptionResponse:
    # Verify product exists
    from app.models import Product
    product_result = await db.execute(select(Product).where(Product.id == consumption_data.product_id))
    if not product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    consumption = Consumption(**consumption_data.model_dump())
    db.add(consumption)
    await db.commit()
    await db.refresh(consumption)

    return ConsumptionResponse.model_validate(consumption)


@router.post("/bulk", response_model=list[ConsumptionResponse], status_code=status.HTTP_201_CREATED, summary="Bulk create consumption records")
async def bulk_create_consumption(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    bulk_data: ConsumptionBulkCreate,
) -> list[ConsumptionResponse]:
    consumptions = [Consumption(**item.model_dump()) for item in bulk_data.items]
    db.add_all(consumptions)
    await db.commit()
    for c in consumptions:
        await db.refresh(c)
    return [ConsumptionResponse.model_validate(c) for c in consumptions]


@router.post("/import", summary="Import consumption from CSV")
async def import_consumption(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    import csv
    import io

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported. Upload a .csv file.",
        )

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    required_cols = {"product_id", "consumption_date", "quantity", "department"}
    if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV must have columns: {', '.join(sorted(required_cols))}. Found: {reader.fieldnames}",
        )

    created = []
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            product_id = row["product_id"].strip()
            quantity = int(row["quantity"].strip())
            department = row["department"].strip()
            prescription_type = row.get("prescription_type", "routine").strip()
            consumption_date = row["consumption_date"].strip()

            if quantity <= 0:
                errors.append({"row": row_num, "error": "Quantity must be > 0"})
                continue

            if department not in ("icu", "er", "ward", "outpatient"):
                errors.append({"row": row_num, "error": f"Invalid department: {department}"})
                continue

            if prescription_type not in ("routine", "emergency", "prophylactic"):
                prescription_type = "routine"

            from datetime import date as _date
            parts = consumption_date.split("-")
            cons_date = _date(int(parts[0]), int(parts[1]), int(parts[2]))

            from uuid import UUID
            prod_uuid = UUID(product_id)

            product_result = await db.execute(select(Product).where(Product.id == prod_uuid))
            if not product_result.scalar_one_or_none():
                errors.append({"row": row_num, "error": f"Product not found: {product_id}"})
                continue

            consumption = Consumption(
                product_id=prod_uuid,
                consumption_date=cons_date,
                quantity=quantity,
                department=department,
                prescription_type=prescription_type,
            )
            db.add(consumption)
            created.append(row_num)

        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})

    if created:
        await db.commit()

    return {
        "imported": len(created),
        "errors": len(errors),
        "error_details": errors[:20],
    }