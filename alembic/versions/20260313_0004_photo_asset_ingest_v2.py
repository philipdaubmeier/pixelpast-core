"""Extend canonical photo ingestion support with richer asset metadata."""

import sqlalchemy as sa

from alembic import op

revision = "20260313_0004"
down_revision = "20260312_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add canonical fields needed for richer photo metadata ingestion."""

    with op.batch_alter_table("person") as batch_op:
        batch_op.add_column(sa.Column("path", sa.String(length=1024), nullable=True))
        batch_op.create_unique_constraint("uq_person_path", ["path"])

    with op.batch_alter_table("tag") as batch_op:
        batch_op.create_unique_constraint("uq_tag_path", ["path"])

    with op.batch_alter_table("asset") as batch_op:
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("creator_person_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_asset_creator_person_id_person",
            "person",
            ["creator_person_id"],
            ["id"],
        )


def downgrade() -> None:
    """Remove richer photo-ingestion canonical fields."""

    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_constraint(
            "fk_asset_creator_person_id_person",
            type_="foreignkey",
        )
        batch_op.drop_column("creator_person_id")
        batch_op.drop_column("summary")

    with op.batch_alter_table("tag") as batch_op:
        batch_op.drop_constraint("uq_tag_path", type_="unique")

    with op.batch_alter_table("person") as batch_op:
        batch_op.drop_constraint("uq_person_path", type_="unique")
        batch_op.drop_column("path")
