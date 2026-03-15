"""Generalize import_run for ingest and derive job lifecycle tracking."""

import sqlalchemy as sa

from alembic import op

revision = "20260315_0007"
down_revision = "20260314_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace source-bound run identity with generic job/type fields."""

    import_run = sa.table(
        "import_run",
        sa.column("source_id", sa.Integer()),
        sa.column("job", sa.String(length=255)),
        sa.column("type", sa.String(length=20)),
    )
    source = sa.table(
        "source",
        sa.column("id", sa.Integer()),
        sa.column("type", sa.String(length=100)),
    )

    with op.batch_alter_table("import_run") as batch_op:
        batch_op.add_column(sa.Column("job", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("type", sa.String(length=20), nullable=True))

    op.execute(
        import_run.update().values(
            job=sa.select(source.c.type)
            .where(source.c.id == import_run.c.source_id)
            .scalar_subquery()
        )
    )
    op.execute(
        import_run.update()
        .where(import_run.c.job.is_(None))
        .values(job=sa.cast(import_run.c.source_id, sa.String(length=255)))
    )
    op.execute(import_run.update().values(type="ingest"))

    with op.batch_alter_table("import_run") as batch_op:
        batch_op.alter_column(
            "job",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "type",
            existing_type=sa.String(length=20),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_import_run_type",
            "type IN ('ingest', 'derive')",
        )
        batch_op.drop_column("source_id")


def downgrade() -> None:
    """Restore source-bound ingestion runs and drop derive-only records."""

    import_run = sa.table(
        "import_run",
        sa.column("id", sa.Integer()),
        sa.column("job", sa.String(length=255)),
        sa.column("type", sa.String(length=20)),
        sa.column("source_id", sa.Integer()),
    )
    source = sa.table(
        "source",
        sa.column("id", sa.Integer()),
        sa.column("type", sa.String(length=100)),
    )

    with op.batch_alter_table("import_run") as batch_op:
        batch_op.add_column(sa.Column("source_id", sa.Integer(), nullable=True))

    op.execute(
        import_run.update().values(
            source_id=sa.select(source.c.id)
            .where(source.c.type == import_run.c.job)
            .order_by(source.c.id)
            .limit(1)
            .scalar_subquery()
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM import_run WHERE type = 'derive' OR source_id IS NULL"
        )
    )

    with op.batch_alter_table("import_run") as batch_op:
        batch_op.create_foreign_key(None, "source", ["source_id"], ["id"])
        batch_op.alter_column(
            "source_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_constraint("ck_import_run_type", type_="check")
        batch_op.drop_column("type")
        batch_op.drop_column("job")
