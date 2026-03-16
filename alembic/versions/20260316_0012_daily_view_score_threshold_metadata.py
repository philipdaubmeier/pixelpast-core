"""Backfill daily view metadata with score-threshold color mappings."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260316_0012"
down_revision = "20260316_0011"
branch_labels = None
depends_on = None

_DEFAULT_ACTIVITY_SCORE_COLOR_THRESHOLDS = (
    {"activity_score": 1, "color_value": "low"},
    {"activity_score": 35, "color_value": "medium"},
    {"activity_score": 70, "color_value": "high"},
)


def upgrade() -> None:
    """Add the default activity-score threshold mapping to persisted daily views."""

    connection = op.get_bind()
    daily_view_table = sa.table(
        "daily_view",
        sa.column("id", sa.Integer()),
        sa.column("metadata", sa.JSON()),
    )

    rows = list(
        connection.execute(
            sa.select(daily_view_table.c.id, daily_view_table.c.metadata).order_by(
                daily_view_table.c.id
            )
        )
    )
    for row in rows:
        next_metadata = dict(row.metadata) if isinstance(row.metadata, dict) else {}
        next_metadata["activity_score_color_thresholds"] = [
            dict(threshold) for threshold in _DEFAULT_ACTIVITY_SCORE_COLOR_THRESHOLDS
        ]
        connection.execute(
            sa.update(daily_view_table)
            .where(daily_view_table.c.id == row.id)
            .values(metadata=next_metadata)
        )


def downgrade() -> None:
    """Remove the score-threshold mapping from persisted daily-view metadata."""

    connection = op.get_bind()
    daily_view_table = sa.table(
        "daily_view",
        sa.column("id", sa.Integer()),
        sa.column("metadata", sa.JSON()),
    )

    rows = list(
        connection.execute(
            sa.select(daily_view_table.c.id, daily_view_table.c.metadata).order_by(
                daily_view_table.c.id
            )
        )
    )

    for row in rows:
        if not isinstance(row.metadata, dict):
            continue
        next_metadata = dict(row.metadata)
        next_metadata.pop("activity_score_color_thresholds", None)
        connection.execute(
            sa.update(daily_view_table)
            .where(daily_view_table.c.id == row.id)
            .values(metadata=next_metadata)
        )
