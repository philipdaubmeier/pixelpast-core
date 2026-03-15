"""Add the daily view catalog and backfill aggregate references."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260315_0009"
down_revision = "20260315_0008"
branch_labels = None
depends_on = None

_OVERALL_SCOPE = "overall"
_SOURCE_TYPE_SCOPE = "source_type"
_OVERALL_SOURCE_TYPE = "__all__"


def upgrade() -> None:
    """Create the daily view catalog and link existing aggregates to it."""

    op.create_table(
        "daily_view",
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

    connection = op.get_bind()
    legacy_daily_aggregate = sa.table(
        "daily_aggregate",
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
    daily_view_table = sa.table(
        "daily_view",
        sa.column("id", sa.Integer()),
        sa.column("aggregate_scope", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("label", sa.String()),
        sa.column("description", sa.Text()),
    )

    existing_rows = list(
        connection.execute(
            sa.select(
                legacy_daily_aggregate.c.date,
                legacy_daily_aggregate.c.aggregate_scope,
                legacy_daily_aggregate.c.source_type,
                legacy_daily_aggregate.c.total_events,
                legacy_daily_aggregate.c.media_count,
                legacy_daily_aggregate.c.activity_score,
                legacy_daily_aggregate.c.tag_summary,
                legacy_daily_aggregate.c.person_summary,
                legacy_daily_aggregate.c.location_summary,
                legacy_daily_aggregate.c.metadata,
            ).order_by(
                legacy_daily_aggregate.c.aggregate_scope,
                legacy_daily_aggregate.c.source_type,
                legacy_daily_aggregate.c.date,
            )
        )
    )

    identities: dict[tuple[str, str | None], dict[str, object]] = {}
    for row in existing_rows:
        normalized_source_type = _normalize_daily_view_source_type(
            aggregate_scope=row.aggregate_scope,
            source_type=row.source_type,
        )
        identity = (row.aggregate_scope, normalized_source_type)
        if identity not in identities:
            metadata = _build_daily_view_metadata(
                aggregate_scope=row.aggregate_scope,
                source_type=row.source_type,
            )
            identities[identity] = {
                "aggregate_scope": row.aggregate_scope,
                "source_type": normalized_source_type,
                "label": metadata["label"],
                "description": metadata["description"],
            }

    if identities:
        connection.execute(
            sa.insert(daily_view_table),
            list(identities.values()),
        )

    daily_views = list(
        connection.execute(
            sa.select(
                daily_view_table.c.id,
                daily_view_table.c.aggregate_scope,
                daily_view_table.c.source_type,
            )
        )
    )
    identity_to_id = {
        (row.aggregate_scope, row.source_type): row.id for row in daily_views
    }

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

    if existing_rows:
        connection.execute(
            sa.insert(current_daily_aggregate),
            [
                {
                    "date": row.date,
                    "aggregate_scope": row.aggregate_scope,
                    "source_type": row.source_type,
                    "daily_view_id": identity_to_id[
                        (
                            row.aggregate_scope,
                            _normalize_daily_view_source_type(
                                aggregate_scope=row.aggregate_scope,
                                source_type=row.source_type,
                            ),
                        )
                    ],
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

    op.drop_index("ix_daily_aggregate_scope_date", table_name="daily_aggregate")
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


def downgrade() -> None:
    """Remove the daily view catalog and collapse aggregates back to v2 shape."""

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
        sa.PrimaryKeyConstraint("date", "aggregate_scope", "source_type"),
    )

    current_daily_aggregate = sa.table(
        "daily_aggregate",
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
    legacy_daily_aggregate = sa.table(
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
        sa.insert(legacy_daily_aggregate).from_select(
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
                current_daily_aggregate.c.date,
                current_daily_aggregate.c.aggregate_scope,
                current_daily_aggregate.c.source_type,
                current_daily_aggregate.c.total_events,
                current_daily_aggregate.c.media_count,
                current_daily_aggregate.c.activity_score,
                current_daily_aggregate.c.tag_summary,
                current_daily_aggregate.c.person_summary,
                current_daily_aggregate.c.location_summary,
                current_daily_aggregate.c.metadata,
            ),
        )
    )

    op.drop_index("ix_daily_aggregate_view_date", table_name="daily_aggregate")
    op.drop_index("ix_daily_aggregate_scope_date", table_name="daily_aggregate")
    op.drop_table("daily_aggregate")
    op.rename_table("daily_aggregate_v2", "daily_aggregate")
    op.create_index(
        "ix_daily_aggregate_scope_date",
        "daily_aggregate",
        ["aggregate_scope", "source_type", "date"],
        unique=False,
    )
    op.drop_table("daily_view")


def _normalize_daily_view_source_type(
    *,
    aggregate_scope: str,
    source_type: str,
) -> str | None:
    """Return the catalog source type identity for one aggregate row."""

    if aggregate_scope == _OVERALL_SCOPE:
        return None
    return source_type


def _build_daily_view_metadata(
    *,
    aggregate_scope: str,
    source_type: str,
) -> dict[str, str]:
    """Return deterministic metadata for a migrated daily view row."""

    if aggregate_scope == _OVERALL_SCOPE:
        return {
            "label": "Activity",
            "description": "Default heat intensity across all timeline sources.",
        }

    if aggregate_scope != _SOURCE_TYPE_SCOPE or source_type == _OVERALL_SOURCE_TYPE:
        raise ValueError(
            f"Unsupported daily view identity during migration: {aggregate_scope}/{source_type}"
        )

    normalized_source_type = source_type.replace("_", " ").strip()
    return {
        "label": normalized_source_type.title(),
        "description": f"Highlights days with {normalized_source_type} activity.",
    }
