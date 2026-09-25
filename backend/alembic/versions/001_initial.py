"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types using raw SQL with IF NOT EXISTS
    enum_definitions = [
        ('userrole', ['pharmacist', 'manager', 'admin']),
        (
            'productcategory',
            [
                'antibiotic',
                'analgesic',
                'antithrombotic',
                'beta_blocker',
                'ppi',
                'bronchodilator',
                'psycholeptic',
                'ace_inhibitor',
                'corticosteroid',
                'other',
            ],
        ),
        ('movementtype', ['in', 'out', 'adjustment', 'transfer', 'loss', 'expired', 'recalled']),
        ('batchstatus', ['available', 'reserved', 'expired', 'recalled', 'quarantine']),
        ('alerttype', ['shortage_risk', 'expiry_risk', 'overstock', 'reorder_point']),
        ('alertseverity', ['info', 'warning', 'critical']),
        ('prescriptiontype', ['routine', 'emergency', 'prophylactic']),
        ('department', ['icu', 'er', 'ward', 'outpatient']),
    ]

    conn = op.get_bind()
    for enum_name, values in enum_definitions:
        values_str = ', '.join(f"'{v}'" for v in values)
        # PostgreSQL doesn't support CREATE TYPE IF NOT EXISTS, use DO block
        conn.execute(
            sa.text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                    CREATE TYPE {enum_name} AS ENUM ({values_str});
                END IF;
            END $$;
        """)
        )

    # Create users table - use enum type name directly
    op.create_table(
        'users',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column(
            'role',
            postgresql.ENUM(name='userrole', create_type=False),
            nullable=False,
            server_default='pharmacist',
        ),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    # Create warehouses table
    op.create_table(
        'warehouses',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('is_primary', sa.Boolean, default=False, nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    # op.create_index('ix_warehouses_primary', 'warehouses', ['is_primary'], unique=True)  # unique=True on column

    # Create products table
    op.create_table(
        'products',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('sku', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('generic_name', sa.String(255), nullable=True),
        sa.Column(
            'category',
            postgresql.ENUM(name='productcategory', create_type=False),
            nullable=False,
            server_default='other',
        ),
        sa.Column('atc_code', sa.String(20), nullable=True, index=True),
        sa.Column('unit', sa.String(20), nullable=False, server_default='un'),
        sa.Column('unit_cost', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('min_stock_level', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_stock_level', sa.Integer, nullable=False, server_default='100'),
        sa.Column('lead_time_days', sa.Integer, nullable=False, server_default='7'),
        sa.Column('controlled_substance', sa.Boolean, default=False, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('product_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('ix_products_category', 'products', ['category'])
    op.create_index('ix_products_controlled', 'products', ['controlled_substance'])
    op.create_index('ix_products_active', 'products', ['is_active'])

    # Create inventory_batches table
    op.create_table(
        'inventory_batches',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'product_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('products.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'warehouse_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('warehouses.id', ondelete='RESTRICT'),
            nullable=False,
            index=True,
        ),
        sa.Column('batch_number', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False, server_default='0'),
        sa.Column('expiry_date', sa.Date, nullable=False, index=True),
        sa.Column('manufacture_date', sa.Date, nullable=True),
        sa.Column('unit_cost', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column(
            'status',
            postgresql.ENUM(name='batchstatus', create_type=False),
            nullable=False,
            server_default='available',
        ),
        sa.Column(
            'received_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('ix_batches_product_expiry', 'inventory_batches', ['product_id', 'expiry_date'])
    op.create_index('ix_batches_status', 'inventory_batches', ['status'])
    # op.create_index('ix_batches_batch_number', 'inventory_batches', ['batch_number'])  # unique constraint creates index
    op.create_unique_constraint(
        'uq_product_batch', 'inventory_batches', ['product_id', 'batch_number']
    )

    # Create stock_movements table
    op.create_table(
        'stock_movements',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'batch_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('inventory_batches.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('quantity_change', sa.Integer, nullable=False),
        sa.Column(
            'movement_type', postgresql.ENUM(name='movementtype', create_type=False), nullable=False
        ),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index('ix_movements_batch_date', 'stock_movements', ['batch_id', 'created_at'])
    op.create_index('ix_movements_type', 'stock_movements', ['movement_type'])
    op.create_index('ix_movements_reference', 'stock_movements', ['reference_type', 'reference_id'])
    # op.create_index('ix_movements_user', 'stock_movements', ['user_id'])  # index=True on column

    # Create consumption table
    op.create_table(
        'consumption',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'product_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('products.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('consumption_date', sa.Date, nullable=False, index=True),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column(
            'department', postgresql.ENUM(name='department', create_type=False), nullable=False
        ),
        sa.Column(
            'prescription_type',
            postgresql.ENUM(name='prescriptiontype', create_type=False),
            nullable=False,
            server_default='routine',
        ),
        sa.Column('context', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        'ix_consumption_product_date', 'consumption', ['product_id', 'consumption_date']
    )
    op.create_index('ix_consumption_department', 'consumption', ['department'])
    # op.create_index('ix_consumption_date', 'consumption', ['consumption_date'])  # index=True on column

    # Create predictions table
    op.create_table(
        'predictions',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'product_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('products.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('forecast_date', sa.Date, nullable=False, index=True),
        sa.Column('predicted_quantity', sa.Integer, nullable=False),
        sa.Column('confidence_lower', sa.Integer, nullable=False),
        sa.Column('confidence_upper', sa.Integer, nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('mape_score', sa.Float, nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_predictions_product_date', 'predictions', ['product_id', 'forecast_date'])
    op.create_index('ix_predictions_model_version', 'predictions', ['model_version'])
    # op.create_index('ix_predictions_created', 'predictions', ['created_at'])  # index=True on column
    op.create_unique_constraint(
        'uq_product_forecast_model', 'predictions', ['product_id', 'forecast_date', 'model_version']
    )

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'product_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('products.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'alert_type', postgresql.ENUM(name='alerttype', create_type=False), nullable=False
        ),
        sa.Column(
            'severity', postgresql.ENUM(name='alertseverity', create_type=False), nullable=False
        ),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('alert_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('acknowledged', sa.Boolean, default=False, nullable=False),
        sa.Column(
            'acknowledged_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_alerts_product_type', 'alerts', ['product_id', 'alert_type'])
    op.create_index('ix_alerts_severity', 'alerts', ['severity'])
    op.create_index('ix_alerts_acknowledged', 'alerts', ['acknowledged'])
    # op.create_index('ix_alerts_created', 'alerts', ['created_at'])  # index=True on column

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            'actor_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_values', postgresql.JSONB, nullable=True),
        sa.Column('new_values', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_audit_entity', 'audit_logs', ['entity_type', 'entity_id', 'created_at'])
    op.create_index('ix_audit_actor', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_action', 'audit_logs', ['action'])

    # Insert default admin user (password: admin123)
    op.execute("""
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active)
        VALUES (
            gen_random_uuid(),
            'admin@hospital.gov.br',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PZvO.S',
            'Administrador do Sistema',
            'admin',
            true
        )
        ON CONFLICT (email) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('alerts')
    op.drop_table('predictions')
    op.drop_table('consumption')
    op.drop_table('stock_movements')
    op.drop_table('inventory_batches')
    op.drop_table('products')
    op.drop_table('warehouses')
    op.drop_table('users')

    # Drop enum types
    for enum_name in [
        'department',
        'prescriptiontype',
        'alertseverity',
        'alerttype',
        'batchstatus',
        'movementtype',
        'productcategory',
        'userrole',
    ]:
        op.execute(f'DROP TYPE IF EXISTS {enum_name} CASCADE')
