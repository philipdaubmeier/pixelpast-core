"""Add runtime progress fields to import runs for ingest observability."""

import sqlalchemy as sa

from alembic import op

revision = "20260313_0005"
down_revision = "20260313_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add phase, heartbeat and progress payload fields to import runs."""

    with op.batch_alter_table("import_run") as batch_op:
        batch_op.add_column(sa.Column("phase", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(sa.Column("progress", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove runtime progress fields from import runs."""

    with op.batch_alter_table("import_run") as batch_op:
        batch_op.drop_column("progress")
        batch_op.drop_column("last_heartbeat_at")
        batch_op.drop_column("phase")
