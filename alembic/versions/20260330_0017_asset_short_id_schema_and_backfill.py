"""Add canonical asset short ids and backfill existing rows."""

from __future__ import annotations

import hashlib

import sqlalchemy as sa

from alembic import op

revision = "20260330_0017"
down_revision = "20260329_0016"
branch_labels = None
depends_on = None

_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_SHORT_ID_LENGTH = 8
_SHORT_ID_SPACE_SIZE = len(_ALPHABET) ** _SHORT_ID_LENGTH


def upgrade() -> None:
    """Add the public asset short id column and backfill all existing rows."""

    connection = op.get_bind()

    with op.batch_alter_table("asset") as batch_op:
        batch_op.add_column(sa.Column("short_id", sa.String(length=8), nullable=True))

    _backfill_asset_short_ids(connection)

    with op.batch_alter_table("asset") as batch_op:
        batch_op.create_unique_constraint("uq_asset_short_id", ["short_id"])
        batch_op.create_check_constraint(
            "ck_asset_short_id_length",
            "length(short_id) = 8",
        )
        batch_op.alter_column("short_id", nullable=False)

    with op.batch_alter_table(
        "asset",
        recreate="always",
        partial_reordering=[
            (
                "id",
                "short_id",
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
    """Drop the public asset short id column and related constraints."""

    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_constraint("ck_asset_short_id_length", type_="check")
        batch_op.drop_constraint("uq_asset_short_id", type_="unique")
        batch_op.drop_column("short_id")

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


def _backfill_asset_short_ids(connection) -> None:
    asset_table = sa.table(
        "asset",
        sa.column("id", sa.Integer()),
        sa.column("short_id", sa.String(length=8)),
    )

    rows = list(
        connection.execute(
            sa.select(asset_table.c.id, asset_table.c.short_id).order_by(asset_table.c.id)
        ).mappings()
    )
    assigned_short_ids = {
        str(row["short_id"])
        for row in rows
        if row["short_id"] is not None
    }

    for row in rows:
        asset_id = int(row["id"])
        if row["short_id"] is not None:
            continue

        short_id = _allocate_backfilled_short_id(
            asset_id=asset_id,
            assigned_short_ids=assigned_short_ids,
        )
        connection.execute(
            sa.update(asset_table)
            .where(asset_table.c.id == asset_id)
            .values(short_id=short_id)
        )
        assigned_short_ids.add(short_id)


def _allocate_backfilled_short_id(
    *,
    asset_id: int,
    assigned_short_ids: set[str],
) -> str:
    attempt = 0
    while True:
        candidate = build_asset_short_id_candidate(
            seed=f"asset:{asset_id}",
            attempt=attempt,
        )
        if candidate not in assigned_short_ids:
            return candidate
        attempt += 1


def build_asset_short_id_candidate(*, seed: str, attempt: int = 0) -> str:
    payload = f"{seed}:{attempt}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return _encode_base58_fixed(int.from_bytes(digest, byteorder="big") % _SHORT_ID_SPACE_SIZE)


def _encode_base58_fixed(value: int) -> str:
    characters: list[str] = []
    remaining = value

    for _ in range(_SHORT_ID_LENGTH):
        remaining, remainder = divmod(remaining, len(_ALPHABET))
        characters.append(_ALPHABET[remainder])

    characters.reverse()
    return "".join(characters)
