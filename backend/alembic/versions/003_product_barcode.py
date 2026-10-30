"""Add barcode to products

Revision ID: 003
Revises: 002
Create Date: 2026-10-08 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '003'
down_revision: str | None = '002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('products', sa.Column('barcode', sa.String(length=50), nullable=True))
    op.create_index('ix_products_barcode', 'products', ['barcode'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_products_barcode', table_name='products')
    op.drop_column('products', 'barcode')
