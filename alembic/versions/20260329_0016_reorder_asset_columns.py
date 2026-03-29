"""Reorder asset columns so source_id follows the primary key."""

from alembic import op

revision = "20260329_0016"
down_revision = "20260329_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Physically reorder asset columns for deterministic schema layout."""

    with op.batch_alter_table(
        "asset",
        recreate="always",
        partial_reordering=[
            (
                "id",
                "source_id",
                "external_id",
                "media_type",
                "timestamp",
                "summary",
                "latitude",
                "longitude",
                "creator_person_id",
                "metadata",
            )
        ],
    ) as batch_op:
        pass


def downgrade() -> None:
    """Restore the legacy asset column order."""

    with op.batch_alter_table(
        "asset",
        recreate="always",
        partial_reordering=[
            (
                "id",
                "external_id",
                "media_type",
                "timestamp",
                "summary",
                "latitude",
                "longitude",
                "creator_person_id",
                "metadata",
                "source_id",
            )
        ],
    ) as batch_op:
        pass
