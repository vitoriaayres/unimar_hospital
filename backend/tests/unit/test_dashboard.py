"""Test dashboard KPIs metric migration (MAPE -> WAPE)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_kpis_expose_wape_as_primary_metric(client: AsyncClient, auth_headers):
    response = await client.get('/api/v1/dashboard/kpis', headers=auth_headers)
    assert response.status_code == 200

    kpis = response.json()
    assert 'average_wape' in kpis
    assert 'average_mape' not in kpis
    assert 0 <= kpis['average_wape'] <= 1


@pytest.mark.asyncio
async def test_models_endpoint_exposes_wape(client: AsyncClient, auth_headers):
    response = await client.get('/api/v1/predictions/models', headers=auth_headers)
    assert response.status_code == 200

    models = response.json()
    assert models
    assert all('wape' in model and 0 <= model['wape'] <= 1 for model in models)


@pytest.mark.asyncio
async def test_prediction_schema_exposes_wape_score(client: AsyncClient):
    response = await client.get('/openapi.json')
    assert response.status_code == 200

    schemas = response.json()['components']['schemas']
    assert 'wape_score' in schemas['PredictionResponse']['properties']


@pytest.mark.asyncio
async def test_list_predictions_returns_paged_items(client: AsyncClient, auth_headers):
    response = await client.get('/api/v1/predictions', headers=auth_headers)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert {'items', 'total', 'page', 'size', 'pages'} <= set(payload)
