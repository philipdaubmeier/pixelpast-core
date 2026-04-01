import { startTransition, useEffect, useMemo, useState } from "react";
import {
  albumApi,
  type AlbumAssetDetailProjection,
  type AlbumAssetListingProjection,
  type AlbumContextProjection,
  type AlbumTreeNodeProjection,
} from "../../../api/album";
import { PanelCard } from "../../../components/PanelCard";
import { Pill } from "../../../components/Pill";
import {
  buildVisiblePersons,
  buildVisibleTags,
  type PersonPanelItemProjection,
  type TagPanelItemProjection,
} from "../../../projections/exploration";
import type {
  PersonProjection,
  TagProjection,
} from "../../../projections/timeline";
import { MapPanel } from "../../context/components/MapPanel";
import { PersonsPanel } from "../../context/components/PersonsPanel";
import { TagsPanel } from "../../context/components/TagsPanel";
import type { AlbumChromeState, AlbumNodeSelection } from "../types";

type LoadState = "loading" | "ready" | "error";

type PhotoAlbumViewProps = {
  selectedPersons: PersonProjection[];
  selectedTags: TagProjection[];
  selectedPersonIds: string[];
  selectedTagPaths: string[];
  hasPersistentFilters: boolean;
  selection: AlbumNodeSelection | null;
  selectedAssetId: number | null;
  expandedFolderIds: number[];
  expandedCollectionIds: number[];
  onSelectionChange: (selection: AlbumNodeSelection | null) => void;
  onSelectedAssetChange: (assetId: number | null) => void;
  onExpandedFolderIdsChange: (ids: number[]) => void;
  onExpandedCollectionIdsChange: (ids: number[]) => void;
  onTogglePerson: (personId: string) => void;
  onToggleTag: (tagPath: string) => void;
  onChromeStateChange: (state: AlbumChromeState) => void;
};

function formatTimestamp(value: string): string {
  const parsed = new Date(value);

  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function toggleExpandedId(ids: number[], id: number): number[] {
  return ids.includes(id)
    ? ids.filter((candidate) => candidate !== id)
    : [...ids, id];
}

function findNodeBySelection(
  nodes: AlbumTreeNodeProjection[],
  selection: AlbumNodeSelection | null,
  kind: AlbumNodeSelection["kind"],
): AlbumTreeNodeProjection | null {
  if (selection === null || selection.kind !== kind) {
    return null;
  }

  return nodes.find((node) => node.id === selection.id) ?? null;
}

function pickDefaultSelection(
  folderNodes: AlbumTreeNodeProjection[],
  collectionNodes: AlbumTreeNodeProjection[],
): AlbumNodeSelection | null {
  const folderCandidate =
    folderNodes.find((node) => node.assetCount > 0) ?? folderNodes[0] ?? null;
  if (folderCandidate !== null) {
    return { kind: "folder", id: folderCandidate.id };
  }

  const collectionCandidate =
    collectionNodes.find((node) => node.assetCount > 0) ??
    collectionNodes[0] ??
    null;
  if (collectionCandidate !== null) {
    return { kind: "collection", id: collectionCandidate.id };
  }

  return null;
}

function ensureAncestorExpansion(
  nodes: AlbumTreeNodeProjection[],
  selection: AlbumNodeSelection | null,
  expandedIds: number[],
): number[] {
  if (selection === null) {
    return expandedIds;
  }

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const selectedNode = nodeById.get(selection.id);
  if (selectedNode === undefined) {
    return expandedIds;
  }

  const nextExpandedIds = new Set(expandedIds);
  let currentParentId = selectedNode.parentId;

  while (currentParentId !== null) {
    nextExpandedIds.add(currentParentId);
    currentParentId = nodeById.get(currentParentId)?.parentId ?? null;
  }

  return [...nextExpandedIds];
}

function buildAlbumPersons(
  selectedPersons: PersonProjection[],
  context: AlbumContextProjection | null,
  hoveredAssetId: number | null,
): PersonPanelItemProjection[] {
  const hoveredPersonIds = new Set(
    hoveredAssetId !== null
      ? context?.assetContextsByAssetId[hoveredAssetId]?.personIds ?? []
      : [],
  );
  const contextPersons = context?.persons ?? [];

  return buildVisiblePersons(
    selectedPersons,
    contextPersons.filter((person) => hoveredPersonIds.has(person.id)),
    contextPersons,
  );
}

function buildAlbumTags(
  selectedTags: TagProjection[],
  context: AlbumContextProjection | null,
  hoveredAssetId: number | null,
): TagPanelItemProjection[] {
  const hoveredTagPaths = new Set(
    hoveredAssetId !== null
      ? context?.assetContextsByAssetId[hoveredAssetId]?.tagPaths ?? []
      : [],
  );
  const contextTags = (context?.tags ?? []).map((tag) => ({
    path: tag.path,
    label: tag.assetCount > 1 ? `${tag.label} / ${tag.assetCount}` : tag.label,
  }));

  return buildVisibleTags(
    selectedTags,
    contextTags.filter((tag) => hoveredTagPaths.has(tag.path)),
    contextTags,
  );
}

function resolveActiveTransportState(
  states: Array<{
    state: LoadState;
    error: string | null;
  }>,
): Pick<AlbumChromeState, "transportState" | "transportError"> {
  const failed = states.find((entry) => entry.state === "error");
  if (failed !== undefined) {
    return {
      transportState: "error",
      transportError: failed.error,
    };
  }

  if (states.some((entry) => entry.state === "loading")) {
    return {
      transportState: "loading",
      transportError: null,
    };
  }

  return {
    transportState: "ready",
    transportError: null,
  };
}

function TreeSection({
  title,
  nodes,
  selectedNodeId,
  expandedIds,
  onToggleExpanded,
  onSelectNode,
  state,
  error,
}: {
  title: string;
  nodes: AlbumTreeNodeProjection[];
  selectedNodeId: number | null;
  expandedIds: number[];
  onToggleExpanded: (nodeId: number) => void;
  onSelectNode: (nodeId: number) => void;
  state: LoadState;
  error: string | null;
}) {
  const childrenByParentId = useMemo(() => {
    const nextValue = new Map<number | null, AlbumTreeNodeProjection[]>();
    for (const node of nodes) {
      const currentChildren = nextValue.get(node.parentId) ?? [];
      currentChildren.push(node);
      nextValue.set(node.parentId, currentChildren);
    }
    for (const children of nextValue.values()) {
      children.sort((left, right) =>
        left.name.localeCompare(right.name, undefined, { sensitivity: "base" }),
      );
    }
    return nextValue;
  }, [nodes]);

  function renderBranch(parentId: number | null, depth: number): JSX.Element[] {
    return (childrenByParentId.get(parentId) ?? []).flatMap((node) => {
      const isSelected = node.id === selectedNodeId;
      const isExpanded = expandedIds.includes(node.id);
      const hasChildren = node.childCount > 0;

      return [
        <div
          key={node.id}
          className="flex items-center gap-2 rounded-2xl px-2 py-1.5"
          style={{ paddingLeft: `${depth * 0.9 + 0.5}rem` }}
        >
          <button
            type="button"
            onClick={() => (hasChildren ? onToggleExpanded(node.id) : undefined)}
            disabled={!hasChildren}
            className="flex h-6 w-6 items-center justify-center rounded-full text-xs text-slate-500 transition hover:bg-white disabled:cursor-default disabled:opacity-35"
            aria-label={hasChildren ? `Toggle ${node.name}` : `${node.name} has no children`}
          >
            {hasChildren ? (isExpanded ? "-" : "+") : "."}
          </button>
          <button
            type="button"
            onClick={() => onSelectNode(node.id)}
            className={[
              "flex min-w-0 flex-1 items-center justify-between gap-3 rounded-2xl border px-3 py-2 text-left transition",
              isSelected
                ? "border-slate-900 bg-slate-900 text-white shadow-[0_10px_30px_rgba(15,23,42,0.12)]"
                : "border-[color:var(--pp-border)] bg-white/65 text-slate-700 hover:bg-white",
            ].join(" ")}
          >
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium">{node.name}</span>
              <span
                className={[
                  "block truncate text-[11px]",
                  isSelected ? "text-slate-200" : "text-slate-500",
                ].join(" ")}
              >
                {node.path}
              </span>
            </span>
            <span
              className={[
                "shrink-0 rounded-full px-2 py-1 text-[11px] font-semibold",
                isSelected ? "bg-white/15 text-white" : "bg-stone-100 text-slate-600",
              ].join(" ")}
            >
              {node.assetCount}
            </span>
          </button>
        </div>,
        ...(hasChildren && isExpanded ? renderBranch(node.id, depth + 1) : []),
      ];
    });
  }

  return (
    <PanelCard title={title}>
      {state === "loading" ? (
        <div className="flex h-full min-h-28 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          Loading {title.toLowerCase()}.
        </div>
      ) : state === "error" ? (
        <div className="flex h-full min-h-28 items-center justify-center rounded-[22px] border border-rose-200 bg-rose-50 px-4 text-center text-sm text-rose-700">
          {error ?? `Unable to load ${title.toLowerCase()}.`}
        </div>
      ) : nodes.length === 0 ? (
        <div className="flex h-full min-h-28 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          No {title.toLowerCase()} are available.
        </div>
      ) : (
        <div className="thin-scrollbar -mx-1 h-full overflow-y-auto px-1">
          {renderBranch(null, 0)}
        </div>
      )}
    </PanelCard>
  );
}

function AssetMetadataPanel({
  detailState,
  detailError,
  detail,
}: {
  detailState: LoadState;
  detailError: string | null;
  detail: AlbumAssetDetailProjection | null;
}) {
  const metadataRows =
    detail === null
      ? []
      : [
          ["Captured", formatTimestamp(detail.timestamp)],
          ["Camera", detail.camera],
          ["Lens", detail.lens],
          [
            "Aperture",
            detail.apertureFNumber !== null ? `f/${detail.apertureFNumber}` : null,
          ],
          [
            "Shutter",
            detail.shutterSpeedSeconds !== null
              ? `${detail.shutterSpeedSeconds}s`
              : null,
          ],
          [
            "Focal length",
            detail.focalLengthMm !== null ? `${detail.focalLengthMm} mm` : null,
          ],
          ["ISO", detail.iso !== null ? String(detail.iso) : null],
        ].filter((row): row is [string, string] => row[1] !== null);

  return (
    <PanelCard
      title="Metadata"
      description={
        detail?.caption ??
        detail?.description ??
        "Lazy-loaded asset detail for the current focus selection."
      }
    >
      {detailState === "loading" ? (
        <div className="flex h-full min-h-32 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          Loading selected photo detail.
        </div>
      ) : detailState === "error" ? (
        <div className="flex h-full min-h-32 items-center justify-center rounded-[22px] border border-rose-200 bg-rose-50 px-4 text-center text-sm text-rose-700">
          {detailError ?? "Photo detail could not be loaded."}
        </div>
      ) : detail === null ? (
        <div className="flex h-full min-h-32 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          Select a thumbnail to inspect metadata and face regions.
        </div>
      ) : (
        <div className="thin-scrollbar flex h-full flex-col gap-3 overflow-y-auto pr-1">
          <div className="rounded-[22px] border border-[color:var(--pp-border)] bg-white/70 px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-900">{detail.title}</h3>
            <p className="mt-1 text-xs text-slate-500">
              {detail.sourceName} / {detail.sourceType}
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-2">
            {metadataRows.map(([label, value]) => (
              <div
                key={label}
                className="rounded-[20px] border border-[color:var(--pp-border)] bg-white/60 px-3 py-2"
              >
                <dt className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  {label}
                </dt>
                <dd className="mt-1 text-sm text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
          {detail.people.length > 0 ? (
            <div className="rounded-[22px] border border-[color:var(--pp-border)] bg-white/60 px-3 py-3">
              <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
                People In Focus
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {detail.people.map((person) => (
                  <Pill key={person.id} muted>
                    {person.name}
                  </Pill>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </PanelCard>
  );
}

function FocusImage({
  detail,
  hoveredFaceName,
}: {
  detail: AlbumAssetDetailProjection;
  hoveredFaceName: string | null;
}) {
  return (
    <div className="relative overflow-hidden rounded-[30px] border border-[color:var(--pp-border)] bg-stone-950/90 shadow-[0_24px_60px_rgba(15,23,42,0.2)]">
      <img
        src={detail.originalUrl}
        alt={detail.title}
        className="max-h-[34rem] w-full object-contain"
      />
      {detail.faceRegions.map((region) => (
        <div
          key={`${region.name}-${region.left}-${region.top}`}
          className="pointer-events-none absolute border-2 border-amber-400 bg-amber-200/10 shadow-[0_0_0_1px_rgba(255,255,255,0.25)]"
          style={{
            left: `${region.left * 100}%`,
            top: `${region.top * 100}%`,
            width: `${(region.right - region.left) * 100}%`,
            height: `${(region.bottom - region.top) * 100}%`,
            opacity:
              hoveredFaceName === null || hoveredFaceName === region.name ? 1 : 0.32,
          }}
        >
          <span className="absolute left-1 top-1 rounded-full bg-amber-400 px-2 py-0.5 text-[10px] font-semibold text-slate-950">
            {region.name}
          </span>
        </div>
      ))}
    </div>
  );
}

export function PhotoAlbumView({
  selectedPersons,
  selectedTags,
  selectedPersonIds,
  selectedTagPaths,
  hasPersistentFilters,
  selection,
  selectedAssetId,
  expandedFolderIds,
  expandedCollectionIds,
  onSelectionChange,
  onSelectedAssetChange,
  onExpandedFolderIdsChange,
  onExpandedCollectionIdsChange,
  onTogglePerson,
  onToggleTag,
  onChromeStateChange,
}: PhotoAlbumViewProps) {
  const [folderTreeState, setFolderTreeState] = useState<LoadState>("loading");
  const [folderTreeError, setFolderTreeError] = useState<string | null>(null);
  const [folderNodes, setFolderNodes] = useState<AlbumTreeNodeProjection[]>([]);
  const [collectionTreeState, setCollectionTreeState] =
    useState<LoadState>("loading");
  const [collectionTreeError, setCollectionTreeError] = useState<string | null>(
    null,
  );
  const [collectionNodes, setCollectionNodes] = useState<AlbumTreeNodeProjection[]>(
    [],
  );
  const [listingState, setListingState] = useState<LoadState>("loading");
  const [listingError, setListingError] = useState<string | null>(null);
  const [listing, setListing] = useState<AlbumAssetListingProjection | null>(
    null,
  );
  const [contextState, setContextState] = useState<LoadState>("loading");
  const [contextError, setContextError] = useState<string | null>(null);
  const [context, setContext] = useState<AlbumContextProjection | null>(null);
  const [detailState, setDetailState] = useState<LoadState>("ready");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detail, setDetail] = useState<AlbumAssetDetailProjection | null>(null);
  const [hoveredAssetId, setHoveredAssetId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    startTransition(() => {
      setFolderTreeState("loading");
      setFolderTreeError(null);
      setCollectionTreeState("loading");
      setCollectionTreeError(null);
    });

    void Promise.all([
      albumApi.getFolderTree({
        selectedPersons: selectedPersonIds,
        selectedTags: selectedTagPaths,
      }),
      albumApi.getCollectionTree({
        selectedPersons: selectedPersonIds,
        selectedTags: selectedTagPaths,
      }),
    ])
      .then(([nextFolderNodes, nextCollectionNodes]) => {
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setFolderNodes(nextFolderNodes);
          setCollectionNodes(nextCollectionNodes);
          setFolderTreeState("ready");
          setCollectionTreeState("ready");
        });

        const stillValidSelection =
          selection !== null &&
          (selection.kind === "folder"
            ? nextFolderNodes.some((node) => node.id === selection.id)
            : nextCollectionNodes.some((node) => node.id === selection.id));

        if (!stillValidSelection) {
          onSelectionChange(
            pickDefaultSelection(nextFolderNodes, nextCollectionNodes),
          );
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Unable to load album navigation.";
        startTransition(() => {
          setFolderTreeState("error");
          setFolderTreeError(message);
          setCollectionTreeState("error");
          setCollectionTreeError(message);
        });
      });

    return () => {
      cancelled = true;
    };
  }, [onSelectionChange, selectedPersonIds, selectedTagPaths, selection]);

  useEffect(() => {
    if (selection === null) {
      startTransition(() => {
        setListingState("ready");
        setListing(null);
        setContextState("ready");
        setContext(null);
        setHoveredAssetId(null);
      });
      return;
    }

    let cancelled = false;

    startTransition(() => {
      setListingState("loading");
      setListingError(null);
      setContextState("loading");
      setContextError(null);
      setHoveredAssetId(null);
    });

    const listingRequest =
      selection.kind === "folder"
        ? albumApi.getFolderListing(selection.id, {
            selectedPersons: selectedPersonIds,
            selectedTags: selectedTagPaths,
          })
        : albumApi.getCollectionListing(selection.id, {
            selectedPersons: selectedPersonIds,
            selectedTags: selectedTagPaths,
          });
    const contextRequest =
      selection.kind === "folder"
        ? albumApi.getFolderContext(selection.id, {
            selectedPersons: selectedPersonIds,
            selectedTags: selectedTagPaths,
          })
        : albumApi.getCollectionContext(selection.id, {
            selectedPersons: selectedPersonIds,
            selectedTags: selectedTagPaths,
          });

    void Promise.all([listingRequest, contextRequest])
      .then(([nextListing, nextContext]) => {
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setListing(nextListing);
          setListingState("ready");
          setContext(nextContext);
          setContextState("ready");
        });

        if (
          selectedAssetId !== null &&
          !nextListing.items.some((item) => item.id === selectedAssetId)
        ) {
          onSelectedAssetChange(null);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Unable to load album selection.";
        startTransition(() => {
          setListingState("error");
          setListingError(message);
          setContextState("error");
          setContextError(message);
        });
      });

    return () => {
      cancelled = true;
    };
  }, [
    onSelectedAssetChange,
    selectedAssetId,
    selectedPersonIds,
    selectedTagPaths,
    selection,
  ]);

  useEffect(() => {
    if (selectedAssetId === null) {
      startTransition(() => {
        setDetailState("ready");
        setDetailError(null);
        setDetail(null);
      });
      return;
    }

    let cancelled = false;

    startTransition(() => {
      setDetailState("loading");
      setDetailError(null);
    });

    void albumApi
      .getAssetDetail(selectedAssetId)
      .then((nextDetail) => {
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setDetail(nextDetail);
          setDetailState("ready");
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setDetailState("error");
          setDetailError(
            error instanceof Error
              ? error.message
              : "Unable to load asset detail.",
          );
        });
      });

    return () => {
      cancelled = true;
    };
  }, [selectedAssetId]);

  useEffect(() => {
    const folderSelection = findNodeBySelection(folderNodes, selection, "folder");
    if (folderSelection !== null) {
      onExpandedFolderIdsChange(
        ensureAncestorExpansion(folderNodes, selection, expandedFolderIds),
      );
    }

    const collectionSelection = findNodeBySelection(
      collectionNodes,
      selection,
      "collection",
    );
    if (collectionSelection !== null) {
      onExpandedCollectionIdsChange(
        ensureAncestorExpansion(collectionNodes, selection, expandedCollectionIds),
      );
    }
  }, [
    collectionNodes,
    expandedCollectionIds,
    expandedFolderIds,
    folderNodes,
    onExpandedCollectionIdsChange,
    onExpandedFolderIdsChange,
    selection,
  ]);

  const visiblePersons = useMemo(
    () => buildAlbumPersons(selectedPersons, context, hoveredAssetId),
    [context, hoveredAssetId, selectedPersons],
  );
  const visibleTags = useMemo(
    () => buildAlbumTags(selectedTags, context, hoveredAssetId),
    [context, hoveredAssetId, selectedTags],
  );
  const hoveredAssetContext =
    hoveredAssetId !== null
      ? context?.assetContextsByAssetId[hoveredAssetId] ?? null
      : null;
  const activeSelectionLabel =
    listing?.selection.name ?? context?.selection.name ?? null;
  const activeTransportState = resolveActiveTransportState([
    { state: folderTreeState, error: folderTreeError },
    { state: collectionTreeState, error: collectionTreeError },
    { state: listingState, error: listingError },
    { state: contextState, error: contextError },
    ...(selectedAssetId !== null
      ? [{ state: detailState, error: detailError }]
      : []),
  ]);

  useEffect(() => {
    const hoveredAssetTitle =
      hoveredAssetId !== null
        ? listing?.items.find((item) => item.id === hoveredAssetId)?.title ?? null
        : null;
    onChromeStateChange({
      transportState: activeTransportState.transportState,
      transportError: activeTransportState.transportError,
      resultSummary:
        listing === null
          ? "Select a folder or collection"
          : `${listing.selection.assetCount} matching asset${
              listing.selection.assetCount === 1 ? "" : "s"
            }`,
      hoverLabel: hoveredAssetTitle ?? detail?.title ?? "not active",
    });
  }, [
    activeTransportState,
    detail?.title,
    hoveredAssetId,
    listing,
    onChromeStateChange,
  ]);

  return (
    <div className="grid h-full min-h-0 gap-2 xl:grid-cols-[19rem_minmax(0,1fr)_23rem]">
      <aside className="grid min-h-0 gap-2 xl:grid-rows-[minmax(0,1fr)_minmax(0,1fr)]">
        <TreeSection
          title="Folders"
          nodes={folderNodes}
          selectedNodeId={selection?.kind === "folder" ? selection.id : null}
          expandedIds={expandedFolderIds}
          onToggleExpanded={(nodeId) =>
            onExpandedFolderIdsChange(toggleExpandedId(expandedFolderIds, nodeId))
          }
          onSelectNode={(nodeId) => {
            onSelectionChange({ kind: "folder", id: nodeId });
            onSelectedAssetChange(null);
          }}
          state={folderTreeState}
          error={folderTreeError}
        />
        <TreeSection
          title="Collections"
          nodes={collectionNodes}
          selectedNodeId={selection?.kind === "collection" ? selection.id : null}
          expandedIds={expandedCollectionIds}
          onToggleExpanded={(nodeId) =>
            onExpandedCollectionIdsChange(
              toggleExpandedId(expandedCollectionIds, nodeId),
            )
          }
          onSelectNode={(nodeId) => {
            onSelectionChange({ kind: "collection", id: nodeId });
            onSelectedAssetChange(null);
          }}
          state={collectionTreeState}
          error={collectionTreeError}
        />
      </aside>

      <section className="panel-surface flex min-h-0 flex-col overflow-hidden p-3 lg:p-3.5">
        <div className="flex items-start justify-between gap-4 border-b border-[color:rgba(98,80,46,0.12)] pb-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-950">
              {listing?.selection.name ?? "Photo Album"}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {listing?.selection.path ??
                "Browse source folders and Lightroom collections without leaving the shared exploration shell."}
            </p>
          </div>
          {selectedAssetId !== null ? (
            <button
              type="button"
              onClick={() => onSelectedAssetChange(null)}
              className="rounded-full border border-[color:var(--pp-border)] bg-white/75 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-white"
            >
              Back to grid
            </button>
          ) : null}
        </div>
        <div className="mt-3 min-h-0 flex-1">
          {listingState === "loading" ? (
            <div className="flex h-full min-h-[18rem] items-center justify-center rounded-[28px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-6 text-center text-sm text-slate-500">
              Loading album assets for the current selection.
            </div>
          ) : listingState === "error" ? (
            <div className="flex h-full min-h-[18rem] items-center justify-center rounded-[28px] border border-rose-200 bg-rose-50 px-6 text-center text-sm text-rose-700">
              {listingError ?? "Album assets could not be loaded."}
            </div>
          ) : listing === null ? (
            <div className="flex h-full min-h-[18rem] items-center justify-center rounded-[28px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-6 text-center text-sm text-slate-500">
              Select a folder or collection to open the album surface.
            </div>
          ) : listing.items.length === 0 ? (
            <div className="flex h-full min-h-[18rem] items-center justify-center rounded-[28px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-6 text-center text-sm text-slate-500">
              No assets matched the current global filters in this selection.
            </div>
          ) : selectedAssetId !== null && detail !== null ? (
            <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-3">
              <div className="min-h-0 overflow-auto pr-1">
                <FocusImage
                  detail={detail}
                  hoveredFaceName={
                    hoveredAssetContext?.personIds.length === 1
                      ? detail.people.find(
                          (person) =>
                            person.id === hoveredAssetContext.personIds[0],
                        )?.name ?? null
                      : null
                  }
                />
              </div>
              <div className="thin-scrollbar flex gap-3 overflow-x-auto pb-1">
                {listing.items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onMouseEnter={() => setHoveredAssetId(item.id)}
                    onMouseLeave={() => setHoveredAssetId(null)}
                    onClick={() => onSelectedAssetChange(item.id)}
                    className={[
                      "group w-28 shrink-0 rounded-[24px] border p-2 text-left transition",
                      item.id === selectedAssetId
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-[color:var(--pp-border)] bg-white/70 text-slate-700 hover:bg-white",
                    ].join(" ")}
                  >
                    <img
                      src={item.thumbnailUrl}
                      alt={item.title}
                      className="h-20 w-full rounded-[18px] object-cover"
                    />
                    <div className="mt-2 truncate text-xs font-medium">
                      {item.title}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="thin-scrollbar h-full overflow-y-auto pr-1">
              <div className="grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] gap-3">
                {listing.items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onMouseEnter={() => setHoveredAssetId(item.id)}
                    onMouseLeave={() => setHoveredAssetId(null)}
                    onClick={() => onSelectedAssetChange(item.id)}
                    className="group overflow-hidden rounded-[24px] border border-[color:var(--pp-border)] bg-white/72 p-2 text-left shadow-[0_14px_30px_rgba(61,44,15,0.06)] transition hover:-translate-y-0.5 hover:bg-white"
                  >
                    <img
                      src={item.thumbnailUrl}
                      alt={item.title}
                      className="h-40 w-full rounded-[18px] object-cover"
                    />
                    <div className="px-1 pb-1 pt-3">
                      <div className="truncate text-sm font-medium text-slate-900">
                        {item.title}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {formatTimestamp(item.timestamp)}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <aside className="grid min-h-0 gap-2 xl:grid-rows-[minmax(0,1.05fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_minmax(0,1fr)]">
        <AssetMetadataPanel
          detailState={detailState}
          detailError={detailError}
          detail={detail}
        />
        <PersonsPanel
          persons={visiblePersons}
          contextLabel={activeSelectionLabel}
          contextStatus={contextState}
          contextError={contextError}
          loadingMessage="Loading people linked to this album selection."
          errorMessage="Album person context could not be loaded."
          emptySelectionMessage="No persons are attached to this album selection."
          onTogglePerson={onTogglePerson}
        />
        <TagsPanel
          tags={visibleTags}
          contextLabel={activeSelectionLabel}
          contextStatus={contextState}
          contextError={contextError}
          loadingMessage="Loading tags linked to this album selection."
          errorMessage="Album tag context could not be loaded."
          emptySelectionMessage="No tags are attached to this album selection."
          onToggleTag={onToggleTag}
        />
        <MapPanel
          contextLabel={activeSelectionLabel}
          mapPoints={context?.mapPoints ?? []}
          highlightedPointIds={hoveredAssetContext?.mapPointIds ?? []}
          hasPersistentFilters={hasPersistentFilters}
          contextStatus={contextState}
          contextError={contextError}
          loadingMessage="Loading album map context."
          errorMessage="Album map context could not be loaded."
          emptySelectionMessage="No coordinates are attached to this album selection."
          summary={
            context === null
              ? null
              : {
                  events: 0,
                  assets: context.summaryCounts.assets,
                  places: context.summaryCounts.places,
                }
          }
        />
      </aside>
    </div>
  );
}
