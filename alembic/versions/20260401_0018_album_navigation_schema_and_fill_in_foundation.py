"""Add album-navigation storage and backfill from existing asset metadata."""

from __future__ import annotations

from pathlib import PurePosixPath

import sqlalchemy as sa

from alembic import op

revision = "20260401_0018"
down_revision = "20260330_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create album-navigation tables and hydrate them from existing assets."""

    connection = op.get_bind()
    inspector = sa.inspect(connection)
    _drop_leftover_batch_table(connection=connection, table_name="_alembic_tmp_asset")

    if not inspector.has_table("asset_folder"):
        op.create_table(
            "asset_folder",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "source_id",
                sa.Integer(),
                sa.ForeignKey("source.id"),
                nullable=False,
            ),
            sa.Column(
                "parent_id",
                sa.Integer(),
                sa.ForeignKey("asset_folder.id"),
                nullable=True,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("path", sa.String(length=2048), nullable=False),
            sa.UniqueConstraint("source_id", "path", name="uq_asset_folder_source_path"),
        )
    if not _has_index(inspector=inspector, table_name="asset_folder", index_name="ix_asset_folder_source_parent"):
        op.create_index(
            "ix_asset_folder_source_parent",
            "asset_folder",
            ["source_id", "parent_id"],
        )

    inspector = sa.inspect(connection)
    if not inspector.has_table("asset_collection"):
        op.create_table(
            "asset_collection",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "source_id",
                sa.Integer(),
                sa.ForeignKey("source.id"),
                nullable=False,
            ),
            sa.Column(
                "parent_id",
                sa.Integer(),
                sa.ForeignKey("asset_collection.id"),
                nullable=True,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("path", sa.String(length=2048), nullable=False),
            sa.Column("external_id", sa.String(length=512), nullable=False),
            sa.Column("collection_type", sa.String(length=100), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.UniqueConstraint(
                "source_id",
                "external_id",
                name="uq_asset_collection_source_external_id",
            ),
            sa.UniqueConstraint(
                "source_id",
                "path",
                name="uq_asset_collection_source_path",
            ),
        )
    if not _has_index(inspector=inspector, table_name="asset_collection", index_name="ix_asset_collection_source_parent"):
        op.create_index(
            "ix_asset_collection_source_parent",
            "asset_collection",
            ["source_id", "parent_id"],
        )

    inspector = sa.inspect(connection)
    if not inspector.has_table("asset_collection_item"):
        op.create_table(
            "asset_collection_item",
            sa.Column(
                "collection_id",
                sa.Integer(),
                sa.ForeignKey("asset_collection.id"),
                nullable=False,
            ),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
            sa.PrimaryKeyConstraint("collection_id", "asset_id"),
            sa.UniqueConstraint(
                "collection_id",
                "asset_id",
                name="uq_asset_collection_item_collection_asset",
            ),
        )
    if not _has_index(inspector=inspector, table_name="asset_collection_item", index_name="ix_asset_collection_item_asset_id"):
        op.create_index(
            "ix_asset_collection_item_asset_id",
            "asset_collection_item",
            ["asset_id"],
        )

    inspector = sa.inspect(connection)
    asset_columns = {column["name"] for column in inspector.get_columns("asset")}
    asset_indexes = {index["name"] for index in inspector.get_indexes("asset")}
    if "folder_id" not in asset_columns:
        _drop_leftover_batch_table(connection=connection, table_name="_alembic_tmp_asset")
        with op.batch_alter_table("asset") as batch_op:
            batch_op.add_column(sa.Column("folder_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_asset_folder_id_asset_folder",
                "asset_folder",
                ["folder_id"],
                ["id"],
            )
            batch_op.create_index("ix_asset_folder_id", ["folder_id"])
    elif "ix_asset_folder_id" not in asset_indexes:
        _drop_leftover_batch_table(connection=connection, table_name="_alembic_tmp_asset")
        with op.batch_alter_table("asset") as batch_op:
            batch_op.create_index("ix_asset_folder_id", ["folder_id"])

    _backfill_album_navigation(connection)

    _drop_leftover_batch_table(connection=connection, table_name="_alembic_tmp_asset")
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
                "folder_id",
                "creator_person_id",
                "metadata",
            )
        ],
    ) as batch_op:
        pass


def downgrade() -> None:
    """Drop album-navigation storage structures."""

    connection = op.get_bind()
    _drop_leftover_batch_table(connection=connection, table_name="_alembic_tmp_asset")

    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_index("ix_asset_folder_id")
        batch_op.drop_constraint("fk_asset_folder_id_asset_folder", type_="foreignkey")
        batch_op.drop_column("folder_id")

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

    op.drop_index("ix_asset_collection_item_asset_id", table_name="asset_collection_item")
    op.drop_table("asset_collection_item")
    op.drop_index("ix_asset_collection_source_parent", table_name="asset_collection")
    op.drop_table("asset_collection")
    op.drop_index("ix_asset_folder_source_parent", table_name="asset_folder")
    op.drop_table("asset_folder")


def _backfill_album_navigation(connection) -> None:
    source_table = sa.table(
        "source",
        sa.column("id", sa.Integer()),
        sa.column("type", sa.String()),
        sa.column("config", sa.JSON()),
    )
    asset_table = sa.table(
        "asset",
        sa.column("id", sa.Integer()),
        sa.column("source_id", sa.Integer()),
        sa.column("external_id", sa.String()),
        sa.column("folder_id", sa.Integer()),
        sa.column("metadata", sa.JSON()),
    )
    asset_folder_table = sa.table(
        "asset_folder",
        sa.column("id", sa.Integer()),
        sa.column("source_id", sa.Integer()),
        sa.column("parent_id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("path", sa.String()),
    )
    asset_collection_table = sa.table(
        "asset_collection",
        sa.column("id", sa.Integer()),
        sa.column("source_id", sa.Integer()),
        sa.column("parent_id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("path", sa.String()),
        sa.column("external_id", sa.String()),
        sa.column("collection_type", sa.String()),
        sa.column("metadata", sa.JSON()),
    )
    asset_collection_item_table = sa.table(
        "asset_collection_item",
        sa.column("collection_id", sa.Integer()),
        sa.column("asset_id", sa.Integer()),
    )

    rows = list(
        connection.execute(
            sa.select(
                asset_table.c.id,
                asset_table.c.source_id,
                asset_table.c.external_id,
                asset_table.c.metadata,
                source_table.c.type,
                source_table.c.config,
            )
            .select_from(
                asset_table.join(source_table, source_table.c.id == asset_table.c.source_id)
            )
            .order_by(asset_table.c.source_id, asset_table.c.id)
        ).mappings()
    )

    folder_cache: dict[tuple[int, str], int] = {}
    collection_cache: dict[tuple[int, str], dict[str, object]] = {}
    collection_path_cache: dict[tuple[int, str], dict[str, object]] = {}
    collection_memberships: set[tuple[int, int]] = set()

    for row in rows:
        metadata = row["metadata"] if isinstance(row["metadata"], dict) else {}
        source_config = row["config"] if isinstance(row["config"], dict) else {}
        folder_path = _extract_folder_path(
            source_type=row["type"],
            metadata=metadata,
            source_config=source_config,
        )
        if folder_path is not None:
            folder_id = _get_or_create_folder_tree(
                connection=connection,
                folder_cache=folder_cache,
                asset_folder_table=asset_folder_table,
                source_id=int(row["source_id"]),
                path=folder_path,
            )
            connection.execute(
                sa.update(asset_table)
                .where(asset_table.c.id == int(row["id"]))
                .values(folder_id=folder_id)
            )

        for collection_spec in _extract_collection_specs(metadata=metadata):
            collection_id = _get_or_create_collection(
                connection=connection,
                collection_cache=collection_cache,
                collection_path_cache=collection_path_cache,
                asset_collection_table=asset_collection_table,
                source_id=int(row["source_id"]),
                collection_spec=collection_spec,
            )
            collection_memberships.add((collection_id, int(row["id"])))

    for collection in sorted(
        collection_path_cache.values(),
        key=lambda item: (str(item["path"]).count("/"), str(item["path"])),
    ):
        parent_path = _parent_navigation_path(str(collection["path"]))
        parent = (
            collection_path_cache.get((int(collection["source_id"]), parent_path))
            if parent_path is not None
            else None
        )
        parent_id = int(parent["id"]) if parent is not None else None
        if collection["parent_id"] == parent_id:
            continue
        connection.execute(
            sa.update(asset_collection_table)
            .where(asset_collection_table.c.id == int(collection["id"]))
            .values(parent_id=parent_id)
        )

    for collection_id, asset_id in sorted(collection_memberships):
        connection.execute(
            sa.insert(asset_collection_item_table).values(
                collection_id=collection_id,
                asset_id=asset_id,
            )
        )


def _get_or_create_folder_tree(
    *,
    connection,
    folder_cache: dict[tuple[int, str], int],
    asset_folder_table,
    source_id: int,
    path: str,
) -> int:
    segments = path.split("/")
    parent_id: int | None = None
    prefix_segments: list[str] = []

    for segment in segments:
        prefix_segments.append(segment)
        current_path = "/".join(prefix_segments)
        cache_key = (source_id, current_path)
        folder_id = folder_cache.get(cache_key)
        if folder_id is None:
            connection.execute(
                sa.insert(asset_folder_table).values(
                    source_id=source_id,
                    parent_id=parent_id,
                    name=segment,
                    path=current_path,
                )
            )
            folder_id = _load_folder_id(
                connection=connection,
                asset_folder_table=asset_folder_table,
                source_id=source_id,
                path=current_path,
            )
            folder_cache[cache_key] = folder_id
        parent_id = folder_id

    return parent_id if parent_id is not None else 0


def _get_or_create_collection(
    *,
    connection,
    collection_cache: dict[tuple[int, str], dict[str, object]],
    collection_path_cache: dict[tuple[int, str], dict[str, object]],
    asset_collection_table,
    source_id: int,
    collection_spec: dict[str, object],
) -> int:
    cache_key = (source_id, str(collection_spec["external_id"]))
    cached = collection_cache.get(cache_key)
    if cached is not None:
        return int(cached["id"])

    connection.execute(
        sa.insert(asset_collection_table).values(
            source_id=source_id,
            parent_id=None,
            name=str(collection_spec["name"]),
            path=str(collection_spec["path"]),
            external_id=str(collection_spec["external_id"]),
            collection_type=str(collection_spec["collection_type"]),
            metadata=collection_spec["metadata"],
        )
    )
    collection_id = _load_collection_id(
        connection=connection,
        asset_collection_table=asset_collection_table,
        source_id=source_id,
        external_id=str(collection_spec["external_id"]),
    )
    collection_cache[cache_key] = {
        "id": collection_id,
        "source_id": source_id,
        "parent_id": None,
        "path": str(collection_spec["path"]),
    }
    collection_path_cache[(source_id, str(collection_spec["path"]))] = collection_cache[
        cache_key
    ]
    return collection_id


def _extract_folder_path(
    *,
    source_type: object,
    metadata: dict[str, object],
    source_config: dict[str, object],
) -> str | None:
    if source_type == "photos":
        source_path = metadata.get("source_path")
        root_path = source_config.get("root_path")
        return _build_photo_folder_path(
            source_path=source_path if isinstance(source_path, str) else None,
            root_path=root_path if isinstance(root_path, str) else None,
        )

    file_path = metadata.get("file_path")
    if isinstance(file_path, str):
        return _normalize_filesystem_folder_path(file_path)
    return None


def _load_folder_id(
    *,
    connection,
    asset_folder_table,
    source_id: int,
    path: str,
) -> int:
    folder_id = connection.execute(
        sa.select(asset_folder_table.c.id)
        .where(asset_folder_table.c.source_id == source_id)
        .where(asset_folder_table.c.path == path)
    ).scalar_one()
    return int(folder_id)


def _load_collection_id(
    *,
    connection,
    asset_collection_table,
    source_id: int,
    external_id: str,
) -> int:
    collection_id = connection.execute(
        sa.select(asset_collection_table.c.id)
        .where(asset_collection_table.c.source_id == source_id)
        .where(asset_collection_table.c.external_id == external_id)
    ).scalar_one()
    return int(collection_id)


def _build_photo_folder_path(
    *,
    source_path: str | None,
    root_path: str | None,
) -> str | None:
    normalized_source_path = _normalize_path_string(source_path)
    if normalized_source_path is None:
        return None

    source_file_path = PurePosixPath(normalized_source_path)
    normalized_root_path = _normalize_path_string(root_path)
    if normalized_root_path is None:
        return _normalize_navigation_path(source_file_path.parent.as_posix())

    root = PurePosixPath(normalized_root_path)
    try:
        relative_parent = source_file_path.parent.relative_to(root)
    except ValueError:
        return _normalize_navigation_path(source_file_path.parent.as_posix())

    segments = [
        segment
        for segment in (root.name, *relative_parent.parts)
        if segment not in {"", "."}
    ]
    return _normalize_navigation_path("/".join(segments))


def _normalize_filesystem_folder_path(file_path: str) -> str | None:
    normalized_file_path = _normalize_path_string(file_path)
    if normalized_file_path is None:
        return None
    parent = PurePosixPath(normalized_file_path).parent
    return _normalize_navigation_path(parent.as_posix())


def _extract_collection_specs(*, metadata: dict[str, object]) -> tuple[dict[str, object], ...]:
    raw_collections = metadata.get("collections")
    if not isinstance(raw_collections, list):
        return ()

    specs: list[dict[str, object]] = []
    seen_external_ids: set[str] = set()
    for raw_collection in raw_collections:
        if not isinstance(raw_collection, dict):
            continue
        external_id = raw_collection.get("id")
        name = raw_collection.get("name")
        path = raw_collection.get("path")
        if external_id is None or not isinstance(name, str) or not isinstance(path, str):
            continue

        normalized_path = _normalize_navigation_path(path)
        external_id_text = str(external_id).strip()
        if normalized_path is None or external_id_text == "" or external_id_text in seen_external_ids:
            continue

        seen_external_ids.add(external_id_text)
        specs.append(
            {
                "external_id": external_id_text,
                "name": name.strip(),
                "path": normalized_path,
                "collection_type": "lightroom_collection",
                "metadata": {"fill_in_source": "asset.metadata.collections"},
            }
        )
    return tuple(sorted(specs, key=lambda spec: (str(spec["path"]).casefold(), str(spec["external_id"]))))


def _normalize_path_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().replace("\\", "/")
    if normalized == "":
        return None
    return normalized


def _normalize_navigation_path(value: str | None) -> str | None:
    normalized = _normalize_path_string(value)
    if normalized is None:
        return None
    segments = [segment.strip() for segment in normalized.split("/") if segment.strip() != ""]
    if not segments:
        return None
    return "/".join(segments)


def _parent_navigation_path(path: str) -> str | None:
    if "/" not in path:
        return None
    parent_path = path.rsplit("/", 1)[0]
    return parent_path or None


def _has_index(*, inspector, table_name: str, index_name: str) -> bool:
    return any(
        index.get("name") == index_name
        for index in inspector.get_indexes(table_name)
    )


def _drop_leftover_batch_table(*, connection, table_name: str) -> None:
    inspector = sa.inspect(connection)
    if inspector.has_table(table_name):
        connection.execute(sa.text(f"DROP TABLE {table_name}"))
