"""Pytest configuration and fixtures for PharmaPredict backend tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import create_app
from app.models import (
    Alert,
    AlertSeverity,
    AlertType,
    BatchStatus,
    Consumption,
    Department,
    InventoryBatch,
    MovementType,
    PrescriptionType,
    Product,
    ProductCategory,
    StockMovement,
    User,
    UserRole,
    Warehouse,
)
from app.utils.security import get_password_hash


# Test database URL (SQLite in memory for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Test Data Factories
# =============================================================================

@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    return {
        "email": "test@hospital.gov.br",
        "password": "TestPass123",
        "full_name": "Test User",
        "role": "pharmacist",
    }


@pytest.fixture
async def test_user(db_session: AsyncSession, sample_user_data: dict) -> User:
    user = User(
        id=uuid4(),
        email=sample_user_data["email"],
        hashed_password=get_password_hash(sample_user_data["password"]),
        full_name=sample_user_data["full_name"],
        role=UserRole(sample_user_data["role"]),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("AdminPass123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def manager_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="manager@test.com",
        hashed_password=get_password_hash("ManagerPass123"),
        full_name="Manager User",
        role=UserRole.MANAGER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    from app.utils.security import create_access_token

    token = create_access_token(
        sub=test_user.id,
        email=test_user.email,
        role=test_user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    from app.utils.security import create_access_token

    token = create_access_token(
        sub=admin_user.id,
        email=admin_user.email,
        role=admin_user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_warehouse(db_session: AsyncSession) -> Warehouse:
    warehouse = Warehouse(
        id=uuid4(),
        name="Almoxarifado Central",
        location="Térreo - Bloco A",
        is_primary=True,
    )
    db_session.add(warehouse)
    await db_session.commit()
    await db_session.refresh(warehouse)
    return warehouse


@pytest.fixture
async def test_product(db_session: AsyncSession) -> Product:
    product = Product(
        id=uuid4(),
        sku="MED-001",
        name="Dipirona 500mg Comprimido",
        generic_name="Dipirona",
        category=ProductCategory.ANALGESIC,
        atc_code="N02BB02",
        unit="mg",
        unit_cost=2.50,
        min_stock_level=100,
        max_stock_level=1000,
        lead_time_days=7,
        controlled_substance=False,
        is_active=True,
        metadata={"base_demand_per_day": 45.0},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_batch(db_session: AsyncSession, test_product: Product, test_warehouse: Warehouse) -> InventoryBatch:
    batch = InventoryBatch(
        id=uuid4(),
        product_id=test_product.id,
        warehouse_id=test_warehouse.id,
        batch_number="L202401001",
        quantity=500,
        expiry_date=date.today() + timedelta(days=365),
        manufacture_date=date.today() - timedelta(days=30),
        unit_cost=2.50,
        status=BatchStatus.AVAILABLE,
    )
    db_session.add(batch)
    await db_session.commit()
    await db_session.refresh(batch)
    return batch


@pytest.fixture
async def test_consumption(db_session: AsyncSession, test_product: Product) -> Consumption:
    consumption = Consumption(
        id=uuid4(),
        product_id=test_product.id,
        consumption_date=date.today() - timedelta(days=1),
        quantity=50,
        department=Department.WARD,
        prescription_type=PrescriptionType.ROUTINE,
        context={"seasonal_multiplier": 1.0},
    )
    db_session.add(consumption)
    await db_session.commit()
    await db_session.refresh(consumption)
    return consumption


@pytest.fixture
async def test_alert(db_session: AsyncSession, test_product: Product) -> Alert:
    alert = Alert(
        id=uuid4(),
        product_id=test_product.id,
        alert_type=AlertType.SHORTAGE_RISK,
        severity=AlertSeverity.WARNING,
        message="Estoque baixo previsto para 5 dias",
        metadata={"days_until_stockout": 5, "recommended_order_qty": 200},
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    return alert


# =============================================================================
# Test Utilities
# =============================================================================

def assert_response_ok(response, expected_status: int = 200):
    """Assert response is successful."""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"


def assert_response_error(response, expected_status: int, error_code: str | None = None):
    """Assert response is an error with optional error code."""
    assert response.status_code == expected_status
    if error_code:
        data = response.json()
        assert data.get("error") == error_code


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def parse_date(date_str: str) -> date:
    """Parse ISO date string."""
    return date.fromisoformat(date_str)