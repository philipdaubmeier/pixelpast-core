"""Revise daily aggregate schema for connector-aware day summaries."""

import sqlalchemy as sa

from alembic import op

revision = "20260314_0006"
down_revision = "20260313_0005"
branch_labels = None
depends_on = None

_OVERALL_SCOPE = "overall"
_SOURCE_TYPE_SCOPE = "source_type"
_OVERALL_SOURCE_TYPE = "__all__"
_EMPTY_JSON_ARRAY = "[]"


def upgrade() -> None:
    """Replace the v1 daily aggregate table with the connector-aware v2 schema."""

    op.create_table(
        "daily_aggregate_v2",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("aggregate_scope", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("total_events", sa.Integer(), nullable=False),
        sa.Column("media_count", sa.Integer(), nullable=False),
        sa.Column("activity_score", sa.Integer(), nullable=False),
        sa.Column("tag_summary", sa.JSON(), nullable=False),
        sa.Column("person_summary", sa.JSON(), nullable=False),
        sa.Column("location_summary", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "aggregate_scope IN ('overall', 'source_type')",
            name="ck_daily_aggregate_scope",
        ),
        sa.CheckConstraint(
            "("
            "aggregate_scope = 'overall' AND source_type = '__all__'"
            ") OR ("
            "aggregate_scope = 'source_type' AND source_type != '__all__'"
            ")",
            name="ck_daily_aggregate_scope_source_type",
        ),
        sa.PrimaryKeyConstraint(
            "date",
            "aggregate_scope",
            "source_type",
        ),
    )

    old_table = sa.table(
        "daily_aggregate",
        sa.column("date", sa.Date()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("metadata", sa.JSON()),
    )
    new_table = sa.table(
        "daily_aggregate_v2",
        sa.column("date", sa.Date()),
        sa.column("aggregate_scope", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("tag_summary", sa.JSON()),
        sa.column("person_summary", sa.JSON()),
        sa.column("location_summary", sa.JSON()),
        sa.column("metadata", sa.JSON()),
    )
    op.execute(
        sa.insert(new_table).from_select(
            [
                "date",
                "aggregate_scope",
                "source_type",
                "total_events",
                "media_count",
                "activity_score",
                "tag_summary",
                "person_summary",
                "location_summary",
                "metadata",
            ],
            sa.select(
                old_table.c.date,
                sa.literal(_OVERALL_SCOPE),
                sa.literal(_OVERALL_SOURCE_TYPE),
                old_table.c.total_events,
                old_table.c.media_count,
                old_table.c.activity_score,
                sa.literal(_EMPTY_JSON_ARRAY),
                sa.literal(_EMPTY_JSON_ARRAY),
                sa.literal(_EMPTY_JSON_ARRAY),
                old_table.c.metadata,
            ),
        )
    )

    op.drop_table("daily_aggregate")
    op.rename_table("daily_aggregate_v2", "daily_aggregate")
    op.create_index(
        "ix_daily_aggregate_scope_date",
        "daily_aggregate",
        ["aggregate_scope", "source_type", "date"],
        unique=False,
    )


def downgrade() -> None:
    """Collapse v2 daily aggregates back to the legacy single-row-per-day table."""

    op.create_table(
        "daily_aggregate_v1",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("total_events", sa.Integer(), nullable=False),
        sa.Column("media_count", sa.Integer(), nullable=False),
        sa.Column("activity_score", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )

    current_table = sa.table(
        "daily_aggregate",
        sa.column("date", sa.Date()),
        sa.column("aggregate_scope", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("metadata", sa.JSON()),
    )
    legacy_table = sa.table(
        "daily_aggregate_v1",
        sa.column("date", sa.Date()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("metadata", sa.JSON()),
    )
    op.execute(
        sa.insert(legacy_table).from_select(
            [
                "date",
                "total_events",
                "media_count",
                "activity_score",
                "metadata",
            ],
            sa.select(
                current_table.c.date,
                current_table.c.total_events,
                current_table.c.media_count,
                current_table.c.activity_score,
                current_table.c.metadata,
            ).where(
                current_table.c.aggregate_scope == _OVERALL_SCOPE,
                current_table.c.source_type == _OVERALL_SOURCE_TYPE,
            ),
        )
    )

    op.drop_index("ix_daily_aggregate_scope_date", table_name="daily_aggregate")
    op.drop_table("daily_aggregate")
    op.rename_table("daily_aggregate_v1", "daily_aggregate")
