"""Drop redundant aggregate identity columns from daily_aggregate."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260316_0010"
down_revision = "20260315_0009"
branch_labels = None
depends_on = None

_OVERALL_SCOPE = "overall"
_OVERALL_SOURCE_TYPE = "__all__"


def upgrade() -> None:
    """Remove aggregate_scope/source_type from daily_aggregate."""

    op.create_table(
        "daily_aggregate_v4",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("daily_view_id", sa.Integer(), nullable=False),
        sa.Column("total_events", sa.Integer(), nullable=False),
        sa.Column("media_count", sa.Integer(), nullable=False),
        sa.Column("activity_score", sa.Integer(), nullable=False),
        sa.Column("tag_summary", sa.JSON(), nullable=False),
        sa.Column("person_summary", sa.JSON(), nullable=False),
        sa.Column("location_summary", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["daily_view_id"], ["daily_view.id"]),
        sa.PrimaryKeyConstraint("date", "daily_view_id"),
    )

    legacy_daily_aggregate = sa.table(
        "daily_aggregate",
        sa.column("date", sa.Date()),
        sa.column("daily_view_id", sa.Integer()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("tag_summary", sa.JSON()),
        sa.column("person_summary", sa.JSON()),
        sa.column("location_summary", sa.JSON()),
        sa.column("metadata", sa.JSON()),
    )
    current_daily_aggregate = sa.table(
        "daily_aggregate_v4",
        sa.column("date", sa.Date()),
        sa.column("daily_view_id", sa.Integer()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("tag_summary", sa.JSON()),
        sa.column("person_summary", sa.JSON()),
        sa.column("location_summary", sa.JSON()),
        sa.column("metadata", sa.JSON()),
    )

    connection = op.get_bind()
    existing_rows = list(
        connection.execute(
            sa.select(
                legacy_daily_aggregate.c.date,
                legacy_daily_aggregate.c.daily_view_id,
                legacy_daily_aggregate.c.total_events,
                legacy_daily_aggregate.c.media_count,
                legacy_daily_aggregate.c.activity_score,
                legacy_daily_aggregate.c.tag_summary,
                legacy_daily_aggregate.c.person_summary,
                legacy_daily_aggregate.c.location_summary,
                legacy_daily_aggregate.c.metadata,
            )
        )
    )
    if existing_rows:
        connection.execute(
            sa.insert(current_daily_aggregate),
            [
                {
                    "date": row.date,
                    "daily_view_id": row.daily_view_id,
                    "total_events": row.total_events,
                    "media_count": row.media_count,
                    "activity_score": row.activity_score,
                    "tag_summary": row.tag_summary,
                    "person_summary": row.person_summary,
                    "location_summary": row.location_summary,
                    "metadata": row.metadata,
                }
                for row in existing_rows
            ],
        )

    op.drop_index("ix_daily_aggregate_view_date", table_name="daily_aggregate")
    op.drop_index("ix_daily_aggregate_scope_date", table_name="daily_aggregate")
    op.drop_table("daily_aggregate")
    op.rename_table("daily_aggregate_v4", "daily_aggregate")
    op.create_index(
        "ix_daily_aggregate_view_date",
        "daily_aggregate",
        ["daily_view_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    """Recreate aggregate_scope/source_type from daily_view."""

    op.create_table(
        "daily_aggregate_v3",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("aggregate_scope", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("daily_view_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["daily_view_id"], ["daily_view.id"]),
        sa.PrimaryKeyConstraint("date", "aggregate_scope", "source_type"),
        sa.UniqueConstraint("date", "daily_view_id", name="uq_daily_aggregate_date_view"),
    )

    current_daily_aggregate = sa.table(
        "daily_aggregate",
        sa.column("date", sa.Date()),
        sa.column("daily_view_id", sa.Integer()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("tag_summary", sa.JSON()),
        sa.column("person_summary", sa.JSON()),
        sa.column("location_summary", sa.JSON()),
        sa.column("metadata", sa.JSON()),
    )
    daily_view_table = sa.table(
        "daily_view",
        sa.column("id", sa.Integer()),
        sa.column("aggregate_scope", sa.String()),
        sa.column("source_type", sa.String()),
    )
    legacy_daily_aggregate = sa.table(
        "daily_aggregate_v3",
        sa.column("date", sa.Date()),
        sa.column("aggregate_scope", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("daily_view_id", sa.Integer()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("tag_summary", sa.JSON()),
        sa.column("person_summary", sa.JSON()),
        sa.column("location_summary", sa.JSON()),
        sa.column("metadata", sa.JSON()),
    )

    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.select(
                current_daily_aggregate.c.date,
                daily_view_table.c.aggregate_scope,
                daily_view_table.c.source_type,
                current_daily_aggregate.c.daily_view_id,
                current_daily_aggregate.c.total_events,
                current_daily_aggregate.c.media_count,
                current_daily_aggregate.c.activity_score,
                current_daily_aggregate.c.tag_summary,
                current_daily_aggregate.c.person_summary,
                current_daily_aggregate.c.location_summary,
                current_daily_aggregate.c.metadata,
            )
            .select_from(
                current_daily_aggregate.join(
                    daily_view_table,
                    daily_view_table.c.id == current_daily_aggregate.c.daily_view_id,
                )
            )
        )
    )
    if rows:
        connection.execute(
            sa.insert(legacy_daily_aggregate),
            [
                {
                    "date": row.date,
                    "aggregate_scope": row.aggregate_scope,
                    "source_type": _materialize_source_type(
                        aggregate_scope=row.aggregate_scope,
                        source_type=row.source_type,
                    ),
                    "daily_view_id": row.daily_view_id,
                    "total_events": row.total_events,
                    "media_count": row.media_count,
                    "activity_score": row.activity_score,
                    "tag_summary": row.tag_summary,
                    "person_summary": row.person_summary,
                    "location_summary": row.location_summary,
                    "metadata": row.metadata,
                }
                for row in rows
            ],
        )

    op.drop_index("ix_daily_aggregate_view_date", table_name="daily_aggregate")
    op.drop_table("daily_aggregate")
    op.rename_table("daily_aggregate_v3", "daily_aggregate")
    op.create_index(
        "ix_daily_aggregate_scope_date",
        "daily_aggregate",
        ["aggregate_scope", "source_type", "date"],
        unique=False,
    )
    op.create_index(
        "ix_daily_aggregate_view_date",
        "daily_aggregate",
        ["daily_view_id", "date"],
        unique=False,
    )


def _materialize_source_type(*, aggregate_scope: str, source_type: str | None) -> str:
    """Return the legacy source_type value reconstructed from daily_view."""

    if aggregate_scope == _OVERALL_SCOPE:
        return _OVERALL_SOURCE_TYPE
    assert source_type is not None
    return source_type
