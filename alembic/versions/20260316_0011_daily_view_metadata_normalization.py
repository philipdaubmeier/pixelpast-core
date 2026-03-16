"""Move redundant daily aggregate metadata onto daily_view."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260316_0011"
down_revision = "20260316_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Move duplicate aggregate metadata into the daily_view catalog."""

    op.add_column(
        "daily_view",
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    connection = op.get_bind()
    daily_view_table = sa.table(
        "daily_view",
        sa.column("id", sa.Integer()),
        sa.column("metadata", sa.JSON()),
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

    representative_rows = list(
        connection.execute(
            sa.select(
                current_daily_aggregate.c.daily_view_id,
                current_daily_aggregate.c.metadata,
            ).order_by(
                current_daily_aggregate.c.daily_view_id,
                current_daily_aggregate.c.date,
            )
        )
    )
    metadata_by_view_id: dict[int, object] = {}
    for row in representative_rows:
        metadata_by_view_id.setdefault(
            row.daily_view_id,
            row.metadata if row.metadata is not None else {},
        )

    for daily_view_id, metadata in metadata_by_view_id.items():
        connection.execute(
            sa.update(daily_view_table)
            .where(daily_view_table.c.id == daily_view_id)
            .values(metadata=metadata),
        )

    op.execute("PRAGMA foreign_keys=OFF")
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
        sa.ForeignKeyConstraint(["daily_view_id"], ["daily_view.id"]),
        sa.PrimaryKeyConstraint("date", "daily_view_id"),
    )

    next_daily_aggregate = sa.table(
        "daily_aggregate_v4",
        sa.column("date", sa.Date()),
        sa.column("daily_view_id", sa.Integer()),
        sa.column("total_events", sa.Integer()),
        sa.column("media_count", sa.Integer()),
        sa.column("activity_score", sa.Integer()),
        sa.column("tag_summary", sa.JSON()),
        sa.column("person_summary", sa.JSON()),
        sa.column("location_summary", sa.JSON()),
    )
    op.execute(
        sa.insert(next_daily_aggregate).from_select(
            [
                "date",
                "daily_view_id",
                "total_events",
                "media_count",
                "activity_score",
                "tag_summary",
                "person_summary",
                "location_summary",
            ],
            sa.select(
                current_daily_aggregate.c.date,
                current_daily_aggregate.c.daily_view_id,
                current_daily_aggregate.c.total_events,
                current_daily_aggregate.c.media_count,
                current_daily_aggregate.c.activity_score,
                current_daily_aggregate.c.tag_summary,
                current_daily_aggregate.c.person_summary,
                current_daily_aggregate.c.location_summary,
            ),
        )
    )

    op.drop_index("ix_daily_aggregate_view_date", table_name="daily_aggregate")
    op.drop_table("daily_aggregate")
    op.rename_table("daily_aggregate_v4", "daily_aggregate")
    op.create_index(
        "ix_daily_aggregate_view_date",
        "daily_aggregate",
        ["daily_view_id", "date"],
        unique=False,
    )
    op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    """Restore duplicate aggregate metadata from daily_view onto each aggregate row."""

    connection = op.get_bind()
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
    )
    current_daily_view = sa.table(
        "daily_view",
        sa.column("id", sa.Integer()),
        sa.column("aggregate_scope", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("label", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("metadata", sa.JSON()),
    )

    op.execute("PRAGMA foreign_keys=OFF")
    op.create_table(
        "daily_aggregate_v3",
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
        "daily_aggregate_v3",
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
    op.execute(
        sa.insert(legacy_daily_aggregate).from_select(
            [
                "date",
                "daily_view_id",
                "total_events",
                "media_count",
                "activity_score",
                "tag_summary",
                "person_summary",
                "location_summary",
                "metadata",
            ],
            sa.select(
                current_daily_aggregate.c.date,
                current_daily_aggregate.c.daily_view_id,
                current_daily_aggregate.c.total_events,
                current_daily_aggregate.c.media_count,
                current_daily_aggregate.c.activity_score,
                current_daily_aggregate.c.tag_summary,
                current_daily_aggregate.c.person_summary,
                current_daily_aggregate.c.location_summary,
                current_daily_view.c.metadata,
            ).select_from(
                current_daily_aggregate.join(
                    current_daily_view,
                    current_daily_view.c.id == current_daily_aggregate.c.daily_view_id,
                )
            ),
        )
    )

    op.create_table(
        "daily_view_v1",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("aggregate_scope", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "aggregate_scope IN ('overall', 'source_type')",
            name="ck_daily_view_scope",
        ),
        sa.CheckConstraint(
            "("
            "aggregate_scope = 'overall' AND source_type IS NULL"
            ") OR ("
            "aggregate_scope = 'source_type' AND source_type IS NOT NULL"
            ")",
            name="ck_daily_view_scope_source_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "aggregate_scope",
            "source_type",
            name="uq_daily_view_scope_source_type",
        ),
    )

    legacy_daily_view = sa.table(
        "daily_view_v1",
        sa.column("id", sa.Integer()),
        sa.column("aggregate_scope", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("label", sa.String()),
        sa.column("description", sa.Text()),
    )
    op.execute(
        sa.insert(legacy_daily_view).from_select(
            ["id", "aggregate_scope", "source_type", "label", "description"],
            sa.select(
                current_daily_view.c.id,
                current_daily_view.c.aggregate_scope,
                current_daily_view.c.source_type,
                current_daily_view.c.label,
                current_daily_view.c.description,
            ),
        )
    )

    op.drop_index("ix_daily_aggregate_view_date", table_name="daily_aggregate")
    op.drop_table("daily_aggregate")
    op.drop_table("daily_view")
    op.rename_table("daily_view_v1", "daily_view")
    op.rename_table("daily_aggregate_v3", "daily_aggregate")
    op.create_index(
        "ix_daily_aggregate_view_date",
        "daily_aggregate",
        ["daily_view_id", "date"],
        unique=False,
    )
    op.execute("PRAGMA foreign_keys=ON")
