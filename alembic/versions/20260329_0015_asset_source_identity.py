"""Make canonical assets source-scoped and backfill source references."""

from __future__ import annotations

import json
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from typing import Any

import sqlalchemy as sa

from alembic import op

revision = "20260329_0015"
down_revision = "20260322_0014"
branch_labels = None
depends_on = None

_PHOTO_SOURCE_TYPE = "photos"
_LIGHTROOM_SOURCE_TYPE = "lightroom_catalog"
_ASSET_SOURCE_TYPES = (_PHOTO_SOURCE_TYPE, _LIGHTROOM_SOURCE_TYPE)


def upgrade() -> None:
    """Backfill asset sources and enforce source-scoped uniqueness."""

    connection = op.get_bind()

    with op.batch_alter_table("asset") as batch_op:
        batch_op.add_column(sa.Column("source_id", sa.Integer(), nullable=True))

    _backfill_asset_source_ids(connection)

    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_constraint("uq_asset_external_id", type_="unique")
        batch_op.create_foreign_key(
            "fk_asset_source_id_source",
            "source",
            ["source_id"],
            ["id"],
        )
        batch_op.create_index("ix_asset_source_id", ["source_id"], unique=False)
        batch_op.create_unique_constraint(
            "uq_asset_source_external_id",
            ["source_id", "external_id"],
        )
        batch_op.alter_column("source_id", nullable=False)


def downgrade() -> None:
    """Drop source-scoped asset identity and restore legacy uniqueness."""

    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_constraint("uq_asset_source_external_id", type_="unique")
        batch_op.drop_index("ix_asset_source_id")
        batch_op.drop_constraint("fk_asset_source_id_source", type_="foreignkey")
        batch_op.create_unique_constraint("uq_asset_external_id", ["external_id"])
        batch_op.drop_column("source_id")


def _backfill_asset_source_ids(connection) -> None:
    source_table = sa.table(
        "source",
        sa.column("id", sa.Integer()),
        sa.column("type", sa.String()),
        sa.column("config", sa.JSON()),
    )
    asset_table = sa.table(
        "asset",
        sa.column("id", sa.Integer()),
        sa.column("external_id", sa.String()),
        sa.column("metadata", sa.JSON()),
        sa.column("source_id", sa.Integer()),
    )

    source_rows = list(
        connection.execute(
            sa.select(
                source_table.c.id,
                source_table.c.type,
                source_table.c.config,
            ).order_by(source_table.c.id)
        ).mappings()
    )
    asset_rows = list(
        connection.execute(
            sa.select(
                asset_table.c.id,
                asset_table.c.external_id,
                asset_table.c.metadata,
            ).order_by(asset_table.c.id)
        ).mappings()
    )

    source_ids_by_type: dict[str, list[int]] = {}
    photo_sources: list[dict[str, Any]] = []
    for row in source_rows:
        source_type = str(row["type"])
        source_ids_by_type.setdefault(source_type, []).append(int(row["id"]))
        if source_type == _PHOTO_SOURCE_TYPE:
            photo_sources.append(
                {
                    "id": int(row["id"]),
                    "root_path": _extract_string(_normalize_json_value(row["config"]), "root_path"),
                }
            )

    fallback_source_id = min((int(row["id"]) for row in source_rows), default=None)
    for row in asset_rows:
        metadata = _normalize_json_value(row["metadata"])
        inferred_source_id = _resolve_asset_source_id(
            external_id=str(row["external_id"]),
            metadata=metadata if isinstance(metadata, dict) else {},
            source_ids_by_type=source_ids_by_type,
            photo_sources=photo_sources,
            fallback_source_id=fallback_source_id,
        )
        if inferred_source_id is None:
            raise RuntimeError(
                f"Could not backfill asset.source_id for asset id {row['id']}."
            )
        connection.execute(
            sa.update(asset_table)
            .where(asset_table.c.id == int(row["id"]))
            .values(source_id=inferred_source_id)
        )


def _resolve_asset_source_id(
    *,
    external_id: str,
    metadata: dict[str, Any],
    source_ids_by_type: dict[str, list[int]],
    photo_sources: list[dict[str, Any]],
    fallback_source_id: int | None,
) -> int | None:
    photo_source_id = _match_photo_source_id(
        external_id=external_id,
        metadata=metadata,
        photo_sources=photo_sources,
    )
    if photo_source_id is not None:
        return photo_source_id

    inferred_source_type = _infer_asset_source_type(
        external_id=external_id,
        metadata=metadata,
        available_source_types=set(source_ids_by_type),
    )
    if inferred_source_type is not None:
        matching_ids = source_ids_by_type.get(inferred_source_type, [])
        if matching_ids:
            return matching_ids[0]

    asset_source_ids = [
        source_id
        for source_type in _ASSET_SOURCE_TYPES
        for source_id in source_ids_by_type.get(source_type, [])
    ]
    if asset_source_ids:
        return min(asset_source_ids)

    return fallback_source_id


def _infer_asset_source_type(
    *,
    external_id: str,
    metadata: dict[str, Any],
    available_source_types: set[str],
) -> str | None:
    if _extract_string(metadata, "source_path") is not None:
        return _PHOTO_SOURCE_TYPE

    if any(
        key in metadata
        for key in (
            "file_name",
            "file_path",
            "preserved_file_name",
            "collections",
            "face_regions",
        )
    ):
        return _LIGHTROOM_SOURCE_TYPE

    if _looks_like_path(external_id) and _PHOTO_SOURCE_TYPE in available_source_types:
        return _PHOTO_SOURCE_TYPE

    configured_asset_source_types = [
        source_type for source_type in _ASSET_SOURCE_TYPES if source_type in available_source_types
    ]
    if len(configured_asset_source_types) == 1:
        return configured_asset_source_types[0]

    return None


def _match_photo_source_id(
    *,
    external_id: str,
    metadata: dict[str, Any],
    photo_sources: list[dict[str, Any]],
) -> int | None:
    candidate_path = _extract_string(metadata, "source_path") or external_id
    if not _looks_like_path(candidate_path):
        return None

    matches = [
        int(source["id"])
        for source in photo_sources
        if _path_is_within(candidate_path, source.get("root_path"))
    ]
    return min(matches) if matches else None


def _path_is_within(candidate_path: str, root_path: str | None) -> bool:
    if root_path is None or not _looks_like_path(root_path):
        return False

    candidate = _normalize_path(candidate_path)
    root = _normalize_path(root_path)
    if candidate is None or root is None:
        return False

    if type(candidate) is not type(root):
        return False

    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _normalize_path(value: str) -> PurePath | None:
    normalized = value.strip()
    if not normalized:
        return None
    if ":" in normalized[:3] or "\\" in normalized:
        return PureWindowsPath(normalized)
    return PurePosixPath(normalized)


def _looks_like_path(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    if not normalized:
        return False
    return (
        normalized.startswith("/")
        or normalized.startswith("\\\\")
        or "\\" in normalized
        or (len(normalized) >= 3 and normalized[1:3] == ":\\")
        or (len(normalized) >= 3 and normalized[1] == ":" and normalized[2] == "/")
    )


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _extract_string(payload: Any, key: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
