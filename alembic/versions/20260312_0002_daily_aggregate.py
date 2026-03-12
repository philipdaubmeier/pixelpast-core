"""Add daily aggregate derived table."""

import sqlalchemy as sa

from alembic import op

revision = "20260312_0002"
down_revision = "20260311_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the daily aggregate table used by derived jobs."""

    op.create_table(
        "daily_aggregate",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("total_events", sa.Integer(), nullable=False),
        sa.Column("media_count", sa.Integer(), nullable=False),
        sa.Column("activity_score", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    """Drop the daily aggregate table."""

    op.drop_table("daily_aggregate")
