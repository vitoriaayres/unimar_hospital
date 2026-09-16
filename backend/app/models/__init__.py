from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    PHARMACIST = "pharmacist"
    MANAGER = "manager"
    ADMIN = "admin"


class ProductCategory(str, enum.Enum):
    ANTIBIOTIC = "antibiotic"
    ANALGESIC = "analgesic"
    ANTITHROMBOTIC = "antithrombotic"
    BETA_BLOCKER = "beta_blocker"
    PPI = "ppi"
    BRONCHODILATOR = "bronchodilator"
    PSYCHOLEPTIC = "psycholeptic"
    ACE_INHIBITOR = "ace_inhibitor"
    CORTICOSTEROID = "corticosteroid"
    OTHER = "other"


class MovementType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    LOSS = "loss"
    EXPIRED = "expired"
    RECALLED = "recalled"


class BatchStatus(str, enum.Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    EXPIRED = "expired"
    RECALLED = "recalled"
    QUARANTINE = "quarantine"


class AlertType(str, enum.Enum):
    SHORTAGE_RISK = "shortage_risk"
    EXPIRY_RISK = "expiry_risk"
    OVERSTOCK = "overstock"
    REORDER_POINT = "reorder_point"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PrescriptionType(str, enum.Enum):
    ROUTINE = "routine"
    EMERGENCY = "emergency"
    PROPHYLACTIC = "prophylactic"


class Department(str, enum.Enum):
    ICU = "icu"
    ER = "er"
    WARD = "ward"
    OUTPATIENT = "outpatient"


def enum_column(enum_class: type[enum.Enum], **kwargs):
    """Create enum column stored as VARCHAR in PostgreSQL.
    values_callable makes SQLAlchemy use enum .value (lowercase) instead of member names (uppercase)."""
    return mapped_column(
        Enum(
            enum_class,
            create_type=False,
            native_enum=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        **kwargs,
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_is_active", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = enum_column(UserRole, nullable=False, default=UserRole.PHARMACIST)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="user")
    acknowledged_alerts: Mapped[list["Alert"]] = relationship(back_populates="acknowledged_by_user")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_sku", "sku", unique=True),
        Index("ix_products_category", "category"),
        Index("ix_products_controlled", "controlled_substance"),
        Index("ix_products_active", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[ProductCategory] = enum_column(ProductCategory, nullable=False, default=ProductCategory.OTHER)
    atc_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="un")
    unit_cost: Mapped[float] = mapped_column(nullable=False, default=0.0)
    min_stock_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_stock_level: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    controlled_substance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    product_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    batches: Mapped[list["InventoryBatch"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    consumptions: Mapped[list["Consumption"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (Index("ix_warehouses_primary", "is_primary", unique=True),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    batches: Mapped[list["InventoryBatch"]] = relationship(back_populates="warehouse")


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    __table_args__ = (
        Index("ix_batches_product_expiry", "product_id", "expiry_date"),
        Index("ix_batches_status", "status"),
        Index("ix_batches_batch_number", "batch_number"),
        UniqueConstraint("product_id", "batch_number", name="uq_product_batch"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    batch_number: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    manufacture_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    unit_cost: Mapped[float] = mapped_column(nullable=False, default=0.0)
    status: Mapped[BatchStatus] = enum_column(BatchStatus, nullable=False, default=BatchStatus.AVAILABLE)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="batches")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="batches")
    movements: Mapped[list["StockMovement"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        Index("ix_movements_batch_date", "batch_id", "created_at"),
        Index("ix_movements_type", "movement_type"),
        Index("ix_movements_reference", "reference_type", "reference_id"),
        Index("ix_movements_user", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("inventory_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[MovementType] = enum_column(MovementType, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    batch: Mapped["InventoryBatch"] = relationship(back_populates="movements")
    user: Mapped[Optional["User"]] = relationship(back_populates="stock_movements")


class Consumption(Base):
    __tablename__ = "consumption"
    __table_args__ = (
        Index("ix_consumption_product_date", "product_id", "consumption_date"),
        Index("ix_consumption_department", "department"),
        Index("ix_consumption_date", "consumption_date"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    consumption_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[Department] = enum_column(Department, nullable=False)
    prescription_type: Mapped[PrescriptionType] = enum_column(PrescriptionType, nullable=False, default=PrescriptionType.ROUTINE)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="consumptions")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_product_date", "product_id", "forecast_date"),
        Index("ix_predictions_model_version", "model_version"),
        Index("ix_predictions_created", "created_at"),
        UniqueConstraint("product_id", "forecast_date", "model_version", name="uq_product_forecast_model"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    predicted_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_lower: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_upper: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    mape_score: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="predictions")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_product_type", "product_id", "alert_type"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_acknowledged", "acknowledged"),
        Index("ix_alerts_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type: Mapped[AlertType] = enum_column(AlertType, nullable=False)
    severity: Mapped[AlertSeverity] = enum_column(AlertSeverity, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="alerts")
    acknowledged_by_user: Mapped[Optional["User"]] = relationship(back_populates="acknowledged_alerts")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id", "created_at"),
        Index("ix_audit_actor", "actor_id"),
        Index("ix_audit_action", "action"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)