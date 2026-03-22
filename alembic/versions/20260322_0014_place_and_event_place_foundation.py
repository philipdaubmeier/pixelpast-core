"""Add derived place cache and event-place association tables."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260322_0014"
down_revision = "20260316_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create place and event-place tables with provider-scoped indexes."""

    op.create_table(
        "place",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("formatted_address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("lastupdate_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"]),
        sa.UniqueConstraint(
            "source_id",
            "external_id",
            name="uq_place_source_external_id",
        ),
    )
    op.create_index(
        "ix_place_source_external_id",
        "place",
        ["source_id", "external_id"],
        unique=False,
    )
    op.create_index("ix_place_lastupdate_at", "place", ["lastupdate_at"], unique=False)
    op.create_index(
        "ix_place_latitude_longitude",
        "place",
        ["latitude", "longitude"],
        unique=False,
    )
    op.create_table(
        "event_place",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"]),
        sa.PrimaryKeyConstraint("event_id", "place_id"),
    )


def downgrade() -> None:
    """Drop the derived place cache and event-place association tables."""

    op.drop_table("event_place")
    op.drop_index("ix_place_latitude_longitude", table_name="place")
    op.drop_index("ix_place_lastupdate_at", table_name="place")
    op.drop_index("ix_place_source_external_id", table_name="place")
    op.drop_table("place")
