"""Add derived album aggregate relevance tables."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260402_0019"
down_revision = "20260401_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create derived album aggregate tables and indexes."""

    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not inspector.has_table("asset_folder_person_group"):
        op.create_table(
            "asset_folder_person_group",
            sa.Column(
                "folder_id",
                sa.Integer(),
                sa.ForeignKey("asset_folder.id"),
                nullable=False,
            ),
            sa.Column(
                "group_id",
                sa.Integer(),
                sa.ForeignKey("person_group.id"),
                nullable=False,
            ),
            sa.Column("matched_person_count", sa.Integer(), nullable=False),
            sa.Column("group_person_count", sa.Integer(), nullable=False),
            sa.Column("matched_asset_count", sa.Integer(), nullable=False),
            sa.Column("matched_creator_person_count", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("folder_id", "group_id"),
        )
    inspector = sa.inspect(connection)
    if not _has_index(
        inspector=inspector,
        table_name="asset_folder_person_group",
        index_name="ix_asset_folder_person_group_group_id",
    ):
        op.create_index(
            "ix_asset_folder_person_group_group_id",
            "asset_folder_person_group",
            ["group_id"],
        )
    if not _has_index(
        inspector=inspector,
        table_name="asset_folder_person_group",
        index_name="ix_asset_folder_person_group_matched_person_count",
    ):
        op.create_index(
            "ix_asset_folder_person_group_matched_person_count",
            "asset_folder_person_group",
            ["matched_person_count"],
        )

    inspector = sa.inspect(connection)
    if not inspector.has_table("asset_collection_person_group"):
        op.create_table(
            "asset_collection_person_group",
            sa.Column(
                "collection_id",
                sa.Integer(),
                sa.ForeignKey("asset_collection.id"),
                nullable=False,
            ),
            sa.Column(
                "group_id",
                sa.Integer(),
                sa.ForeignKey("person_group.id"),
                nullable=False,
            ),
            sa.Column("matched_person_count", sa.Integer(), nullable=False),
            sa.Column("group_person_count", sa.Integer(), nullable=False),
            sa.Column("matched_asset_count", sa.Integer(), nullable=False),
            sa.Column("matched_creator_person_count", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("collection_id", "group_id"),
        )
    inspector = sa.inspect(connection)
    if not _has_index(
        inspector=inspector,
        table_name="asset_collection_person_group",
        index_name="ix_asset_collection_person_group_group_id",
    ):
        op.create_index(
            "ix_asset_collection_person_group_group_id",
            "asset_collection_person_group",
            ["group_id"],
        )
    if not _has_index(
        inspector=inspector,
        table_name="asset_collection_person_group",
        index_name="ix_asset_collection_person_group_matched_person_count",
    ):
        op.create_index(
            "ix_asset_collection_person_group_matched_person_count",
            "asset_collection_person_group",
            ["matched_person_count"],
        )


def downgrade() -> None:
    """Drop derived album aggregate tables and indexes."""

    op.drop_index(
        "ix_asset_collection_person_group_matched_person_count",
        table_name="asset_collection_person_group",
    )
    op.drop_index(
        "ix_asset_collection_person_group_group_id",
        table_name="asset_collection_person_group",
    )
    op.drop_table("asset_collection_person_group")

    op.drop_index(
        "ix_asset_folder_person_group_matched_person_count",
        table_name="asset_folder_person_group",
    )
    op.drop_index(
        "ix_asset_folder_person_group_group_id",
        table_name="asset_folder_person_group",
    )
    op.drop_table("asset_folder_person_group")


def _has_index(*, inspector, table_name: str, index_name: str) -> bool:
    return any(
        index.get("name") == index_name
        for index in inspector.get_indexes(table_name)
    )
