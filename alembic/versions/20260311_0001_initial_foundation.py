"""Initial Alembic foundation revision."""

import sqlalchemy as sa

from alembic import op

revision = "20260311_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the initial canonical schema revision."""

    op.create_table(
        "source",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "asset",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=512), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_asset_timestamp", "asset", ["timestamp"], unique=False)
    op.create_table(
        "import_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"]),
    )
    op.create_table(
        "event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("timestamp_start", sa.DateTime(), nullable=False),
        sa.Column("timestamp_end", sa.DateTime(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("derived_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"]),
    )
    op.create_index("ix_event_source_id", "event", ["source_id"], unique=False)
    op.create_index(
        "ix_event_timestamp_start",
        "event",
        ["timestamp_start"],
        unique=False,
    )
    op.create_index("ix_event_type", "event", ["type"], unique=False)
    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_table(
        "person",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_table(
        "person_group",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_table(
        "event_asset",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["asset.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"]),
        sa.PrimaryKeyConstraint("event_id", "asset_id"),
    )
    op.create_table(
        "event_tag",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"]),
        sa.PrimaryKeyConstraint("event_id", "tag_id"),
    )
    op.create_table(
        "asset_tag",
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["asset.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"]),
        sa.PrimaryKeyConstraint("asset_id", "tag_id"),
    )
    op.create_table(
        "event_person",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"]),
        sa.PrimaryKeyConstraint("event_id", "person_id"),
    )
    op.create_table(
        "asset_person",
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["asset.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"]),
        sa.PrimaryKeyConstraint("asset_id", "person_id"),
    )
    op.create_table(
        "person_group_member",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["person_group.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"]),
        sa.PrimaryKeyConstraint("group_id", "person_id"),
    )


def downgrade() -> None:
    """Revert the initial canonical schema revision."""

    op.drop_table("person_group_member")
    op.drop_table("asset_person")
    op.drop_table("event_person")
    op.drop_table("asset_tag")
    op.drop_table("event_tag")
    op.drop_table("event_asset")
    op.drop_table("person_group")
    op.drop_table("person")
    op.drop_table("tag")
    op.drop_index("ix_event_type", table_name="event")
    op.drop_index("ix_event_timestamp_start", table_name="event")
    op.drop_index("ix_event_source_id", table_name="event")
    op.drop_table("event")
    op.drop_table("import_run")
    op.drop_index("ix_asset_timestamp", table_name="asset")
    op.drop_table("asset")
    op.drop_table("source")
