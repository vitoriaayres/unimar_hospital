"""Test dashboard KPIs metric migration (MAPE -> WAPE)."""

import json

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


@pytest.mark.asyncio
async def test_model_report_returns_charts_data(
    client: AsyncClient, auth_headers, tmp_path, monkeypatch
):
    from app.api.v1 import predictions

    report = {
        'metrics': {'wape': 0.14, 'baseline_wape': 0.19},
        'test_period': {'start': '2025-08-01', 'end': '2026-10-22'},
        'weekly': [{'week': '2025-08-04', 'actual': 100.0, 'predicted': 95.0, 'baseline': 90.0}],
        'by_category': [{'category': 'antibiotic', 'wape': 0.12, 'baseline_wape': 0.18, 'n': 10}],
        'feature_importance': [{'feature': 'lag_7', 'importance': 0.3}],
    }
    (tmp_path / 'model_report_production.json').write_text(json.dumps(report), encoding='utf-8')
    monkeypatch.setattr(predictions, 'DATA_DIR', tmp_path)

    response = await client.get('/api/v1/predictions/model-report', headers=auth_headers)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload['metrics']['wape'] < payload['metrics']['baseline_wape']
    assert payload['weekly'][0]['predicted'] == 95.0


@pytest.mark.asyncio
async def test_model_report_missing_returns_404(
    client: AsyncClient, auth_headers, tmp_path, monkeypatch
):
    from app.api.v1 import predictions

    monkeypatch.setattr(predictions, 'DATA_DIR', tmp_path)

    response = await client.get('/api/v1/predictions/model-report', headers=auth_headers)
    assert response.status_code == 404
