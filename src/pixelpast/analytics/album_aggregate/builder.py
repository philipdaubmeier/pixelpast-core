"""Pure album aggregate snapshot builder."""

from __future__ import annotations

from dataclasses import dataclass, field

from pixelpast.analytics.album_aggregate.loading import AlbumAggregateCanonicalInputs
from pixelpast.persistence.repositories import (
    AssetCollectionPersonGroupSnapshot,
    AssetFolderPersonGroupSnapshot,
)


@dataclass(slots=True, frozen=True)
class AlbumAggregateBuildResult:
    """Deterministic derived relevance rows for folders and collections."""

    folder_rows: tuple[AssetFolderPersonGroupSnapshot, ...]
    collection_rows: tuple[AssetCollectionPersonGroupSnapshot, ...]


@dataclass(slots=True)
class _NodeGroupAccumulator:
    matched_person_ids: set[int] = field(default_factory=set)
    matched_asset_ids: set[int] = field(default_factory=set)
    creator_person_ids: set[int] = field(default_factory=set)


def build_album_aggregate_snapshots(
    inputs: AlbumAggregateCanonicalInputs,
) -> AlbumAggregateBuildResult:
    """Build deterministic folder and collection relevance rows from canonical data."""

    group_person_ids = {
        group.group_id: (
            set(group.person_ids) - set(group.ignored_person_ids)
        )
        for group in inputs.person_groups
        if set(group.person_ids) - set(group.ignored_person_ids)
    }
    groups_by_person_id = _build_groups_by_person_id(group_person_ids=group_person_ids)

    folder_ancestors_by_id = _build_ancestor_chain_by_id(
        {
            node.folder_id: node.parent_id
            for node in inputs.folder_nodes
        }
    )
    collection_ancestors_by_id = _build_ancestor_chain_by_id(
        {
            node.collection_id: node.parent_id
            for node in inputs.collection_nodes
        }
    )
    collection_ids_by_asset_id = _build_collection_ids_by_asset_id(
        collection_memberships=inputs.collection_memberships
    )

    folder_accumulators: dict[tuple[int, int], _NodeGroupAccumulator] = {}
    collection_accumulators: dict[tuple[int, int], _NodeGroupAccumulator] = {}

    for asset in inputs.asset_evidence:
        asset_person_ids = set(asset.person_ids)
        if asset.creator_person_id is not None:
            asset_person_ids.add(asset.creator_person_id)
        if not asset_person_ids:
            continue

        if asset.folder_id is not None:
            _accumulate_node_group_stats(
                accumulators=folder_accumulators,
                node_ids=folder_ancestors_by_id.get(asset.folder_id, ()),
                asset_id=asset.asset_id,
                asset_person_ids=asset_person_ids,
                creator_person_id=asset.creator_person_id,
                groups_by_person_id=groups_by_person_id,
            )

        direct_collection_ids = collection_ids_by_asset_id.get(asset.asset_id, ())
        if direct_collection_ids:
            collection_node_ids: set[int] = set()
            for collection_id in direct_collection_ids:
                collection_node_ids.update(
                    collection_ancestors_by_id.get(collection_id, ())
                )
            _accumulate_node_group_stats(
                accumulators=collection_accumulators,
                node_ids=sorted(collection_node_ids),
                asset_id=asset.asset_id,
                asset_person_ids=asset_person_ids,
                creator_person_id=asset.creator_person_id,
                groups_by_person_id=groups_by_person_id,
            )

    folder_rows = tuple(
        sorted(
            (
                AssetFolderPersonGroupSnapshot(
                    folder_id=node_id,
                    group_id=group_id,
                    matched_person_count=len(accumulator.matched_person_ids),
                    group_person_count=len(group_person_ids[group_id]),
                    matched_asset_count=len(accumulator.matched_asset_ids),
                    matched_creator_person_count=len(accumulator.creator_person_ids),
                )
                for (node_id, group_id), accumulator in folder_accumulators.items()
                if accumulator.matched_person_ids
            ),
            key=lambda row: (row.folder_id, row.group_id),
        )
    )
    collection_rows = tuple(
        sorted(
            (
                AssetCollectionPersonGroupSnapshot(
                    collection_id=node_id,
                    group_id=group_id,
                    matched_person_count=len(accumulator.matched_person_ids),
                    group_person_count=len(group_person_ids[group_id]),
                    matched_asset_count=len(accumulator.matched_asset_ids),
                    matched_creator_person_count=len(accumulator.creator_person_ids),
                )
                for (node_id, group_id), accumulator in collection_accumulators.items()
                if accumulator.matched_person_ids
            ),
            key=lambda row: (row.collection_id, row.group_id),
        )
    )
    return AlbumAggregateBuildResult(
        folder_rows=folder_rows,
        collection_rows=collection_rows,
    )


def _build_groups_by_person_id(
    *,
    group_person_ids: dict[int, set[int]],
) -> dict[int, tuple[int, ...]]:
    grouped: dict[int, list[int]] = {}
    for group_id, person_ids in group_person_ids.items():
        for person_id in person_ids:
            grouped.setdefault(person_id, []).append(group_id)
    return {
        person_id: tuple(sorted(group_ids))
        for person_id, group_ids in grouped.items()
    }


def _build_ancestor_chain_by_id(
    parent_id_by_node_id: dict[int, int | None],
) -> dict[int, tuple[int, ...]]:
    cache: dict[int, tuple[int, ...]] = {}

    def resolve(node_id: int, active: set[int]) -> tuple[int, ...]:
        cached = cache.get(node_id)
        if cached is not None:
            return cached
        if node_id in active:
            raise ValueError(f"Detected cyclic album hierarchy at node {node_id}.")

        active.add(node_id)
        parent_id = parent_id_by_node_id.get(node_id)
        if parent_id is None:
            resolved = (node_id,)
        else:
            resolved = (node_id, *resolve(parent_id, active))
        active.remove(node_id)
        cache[node_id] = resolved
        return resolved

    return {
        node_id: resolve(node_id, set())
        for node_id in sorted(parent_id_by_node_id)
    }


def _build_collection_ids_by_asset_id(
    *,
    collection_memberships,
) -> dict[int, tuple[int, ...]]:
    grouped: dict[int, set[int]] = {}
    for membership in collection_memberships:
        grouped.setdefault(membership.asset_id, set()).add(membership.collection_id)
    return {
        asset_id: tuple(sorted(collection_ids))
        for asset_id, collection_ids in grouped.items()
    }


def _accumulate_node_group_stats(
    *,
    accumulators: dict[tuple[int, int], _NodeGroupAccumulator],
    node_ids,
    asset_id: int,
    asset_person_ids: set[int],
    creator_person_id: int | None,
    groups_by_person_id: dict[int, tuple[int, ...]],
) -> None:
    for node_id in node_ids:
        matched_group_ids_for_asset: set[int] = set()
        for person_id in asset_person_ids:
            for group_id in groups_by_person_id.get(person_id, ()):
                accumulator = accumulators.setdefault(
                    (node_id, group_id),
                    _NodeGroupAccumulator(),
                )
                accumulator.matched_person_ids.add(person_id)
                matched_group_ids_for_asset.add(group_id)
                if creator_person_id == person_id:
                    accumulator.creator_person_ids.add(person_id)
        for group_id in matched_group_ids_for_asset:
            accumulators[(node_id, group_id)].matched_asset_ids.add(asset_id)
