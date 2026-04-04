"""Add derived album node asset counts."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260404_0020"
down_revision = "20260402_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add materialized structural asset counts to album nodes."""

    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _has_column(inspector=inspector, table_name="asset_folder", column_name="asset_count"):
        op.add_column(
            "asset_folder",
            sa.Column("asset_count", sa.Integer(), nullable=False, server_default="0"),
        )

    inspector = sa.inspect(connection)
    if not _has_column(
        inspector=inspector,
        table_name="asset_collection",
        column_name="asset_count",
    ):
        op.add_column(
            "asset_collection",
            sa.Column("asset_count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    """Drop materialized structural asset counts from album nodes."""

    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if _has_column(
        inspector=inspector,
        table_name="asset_collection",
        column_name="asset_count",
    ):
        op.drop_column("asset_collection", "asset_count")

    inspector = sa.inspect(connection)
    if _has_column(inspector=inspector, table_name="asset_folder", column_name="asset_count"):
        op.drop_column("asset_folder", "asset_count")


def _has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(
        column.get("name") == column_name
        for column in inspector.get_columns(table_name)
    )
