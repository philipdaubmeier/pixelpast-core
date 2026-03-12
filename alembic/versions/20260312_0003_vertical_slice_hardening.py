"""Harden canonical uniqueness for the first vertical slice."""

from alembic import op

revision = "20260312_0003"
down_revision = "20260312_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraints backing idempotent ingestion semantics."""

    with op.batch_alter_table("asset") as batch_op:
        batch_op.create_unique_constraint(
            "uq_asset_external_id",
            ["external_id"],
        )
    with op.batch_alter_table("source") as batch_op:
        batch_op.create_unique_constraint(
            "uq_source_type_name",
            ["type", "name"],
        )


def downgrade() -> None:
    """Remove vertical-slice uniqueness constraints."""

    with op.batch_alter_table("source") as batch_op:
        batch_op.drop_constraint("uq_source_type_name", type_="unique")
    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_constraint("uq_asset_external_id", type_="unique")
