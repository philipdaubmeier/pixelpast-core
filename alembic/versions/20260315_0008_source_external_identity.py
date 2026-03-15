"""Add stable external source identity for calendar ingestion."""

import sqlalchemy as sa

from alembic import op

revision = "20260315_0008"
down_revision = "20260315_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add an optional externally unique identifier to canonical sources."""

    with op.batch_alter_table("source") as batch_op:
        batch_op.add_column(sa.Column("external_id", sa.String(length=512), nullable=True))
        batch_op.create_unique_constraint("uq_source_external_id", ["external_id"])


def downgrade() -> None:
    """Drop the canonical external source identifier."""

    with op.batch_alter_table("source") as batch_op:
        batch_op.drop_constraint("uq_source_external_id", type_="unique")
        batch_op.drop_column("external_id")
