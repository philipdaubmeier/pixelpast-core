"""Add optional direct-color and title fields to daily aggregates."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260316_0013"
down_revision = "20260316_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend daily aggregates with nullable direct-color and title columns."""

    with op.batch_alter_table("daily_aggregate", schema=None) as batch_op:
        batch_op.add_column(sa.Column("color_value", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("title", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove the direct-color and title columns from daily aggregates."""

    with op.batch_alter_table("daily_aggregate", schema=None) as batch_op:
        batch_op.drop_column("title")
        batch_op.drop_column("color_value")
