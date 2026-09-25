"""Add wape_score to predictions

Revision ID: 002
Revises: 001
Create Date: 2026-09-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: str | None = '001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('predictions', sa.Column('wape_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('predictions', 'wape_score')
