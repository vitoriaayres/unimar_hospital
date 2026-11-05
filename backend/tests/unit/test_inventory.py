"""Test expiry counts in the inventory summary."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models import BatchStatus, InventoryBatch


@pytest.mark.asyncio
async def test_summary_counts_only_batches_with_stock_per_window(
    client: AsyncClient, auth_headers, db_session, test_product, test_warehouse
):
    batches = [('EMPTY', 0, 10), ('IN30', 50, 20), ('IN90', 50, 60), ('LATER', 50, 200)]
    for number, quantity, days in batches:
        db_session.add(
            InventoryBatch(
                id=uuid4(),
                product_id=test_product.id,
                warehouse_id=test_warehouse.id,
                batch_number=number,
                quantity=quantity,
                expiry_date=date.today() + timedelta(days=days),
                unit_cost=2.50,
                status=BatchStatus.AVAILABLE,
            )
        )
    await db_session.commit()

    response = await client.get('/api/v1/inventory/summary', headers=auth_headers)
    assert response.status_code == 200

    summary = next(r for r in response.json() if r['product_id'] == str(test_product.id))
    assert summary['batches_count'] == 3
    assert summary['batches_expiring_30d'] == 1
    assert summary['batches_expiring_90d'] == 2
