"""Test product endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, admin_auth_headers):
    product_data = {
        "sku": "MED-TEST-001",
        "name": "Test Medicamento 100mg",
        "generic_name": "Test Genérico",
        "category": "antibiotic",
        "atc_code": "J01AA01",
        "unit": "mg",
        "unit_cost": "5.00",
        "min_stock_level": 50,
        "max_stock_level": 500,
        "lead_time_days": 7,
        "controlled_substance": False,
    }
    response = await client.post(
        "/api/v1/products",
        json=product_data,
        headers=admin_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == product_data["sku"]
    assert data["name"] == product_data["name"]
    assert data["category"] == product_data["category"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_product_duplicate_sku(client: AsyncClient, admin_auth_headers, test_product):
    product_data = {
        "sku": test_product.sku,  # Duplicate SKU
        "name": "Another Product",
        "generic_name": "Generic",
        "category": "analgesic",
        "unit": "mg",
        "unit_cost": "3.00",
    }
    response = await client.post(
        "/api/v1/products",
        json=product_data,
        headers=admin_auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, auth_headers, test_product):
    response = await client.get("/api/v1/products", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_products_with_filters(client: AsyncClient, auth_headers, test_product):
    # Filter by category
    response = await client.get(
        "/api/v1/products",
        params={"category": "analgesic"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["category"] == "analgesic"


@pytest.mark.asyncio
async def test_get_product(client: AsyncClient, auth_headers, test_product):
    response = await client.get(f"/api/v1/products/{test_product.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_product.id)
    assert data["sku"] == test_product.sku


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient, auth_headers):
    from uuid import uuid4
    response = await client.get(f"/api/v1/products/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, admin_auth_headers, test_product):
    update_data = {"name": "Updated Name", "unit_cost": "10.00"}
    response = await client.patch(
        f"/api/v1/products/{test_product.id}",
        json=update_data,
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["unit_cost"] == "10.00"


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, admin_auth_headers, test_product):
    response = await client.delete(f"/api/v1/products/{test_product.id}", headers=admin_auth_headers)
    assert response.status_code == 204

    # Verify soft delete
    get_response = await client.get(f"/api/v1/products/{test_product.id}", headers=admin_auth_headers)
    assert get_response.status_code == 404  # Not found because is_active=False