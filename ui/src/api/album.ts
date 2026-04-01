import type { MapPointProjection, PersonProjection, TagProjection } from "../projections/timeline";
import {
  albumTransport,
  resolveBackendUrl,
  type ApiAlbumAssetDetailResponse,
  type ApiAlbumAssetListingResponse,
  type ApiAlbumCollectionNode,
  type ApiAlbumContextResponse,
  type ApiAlbumFolderNode,
  type ApiAlbumSelection,
} from "./albumTransport";

export type AlbumTreeNodeProjection = {
  id: number;
  sourceId: number;
  sourceName: string;
  sourceType: string;
  parentId: number | null;
  name: string;
  path: string;
  childCount: number;
  assetCount: number;
  collectionType: string | null;
};

export type AlbumSelectionProjection = {
  nodeKind: "folder" | "collection";
  id: number;
  sourceId: number;
  sourceName: string;
  sourceType: string;
  parentId: number | null;
  name: string;
  path: string;
  assetCount: number;
  collectionType: string | null;
};

export type AlbumAssetProjection = {
  id: number;
  shortId: string;
  timestamp: string;
  mediaType: string;
  title: string;
  thumbnailUrl: string;
};

export type AlbumAssetListingProjection = {
  selection: AlbumSelectionProjection;
  items: AlbumAssetProjection[];
};

export type AlbumContextPersonProjection = PersonProjection & {
  assetCount: number;
};

export type AlbumContextTagProjection = TagProjection & {
  id: string;
  assetCount: number;
};

export type AlbumContextAssetProjection = {
  assetId: number;
  personIds: string[];
  tagPaths: string[];
  mapPointIds: string[];
};

export type AlbumContextProjection = {
  selection: AlbumSelectionProjection;
  persons: AlbumContextPersonProjection[];
  tags: AlbumContextTagProjection[];
  mapPoints: Array<
    MapPointProjection & {
      assetCount: number;
    }
  >;
  assetContextsByAssetId: Record<number, AlbumContextAssetProjection>;
  summaryCounts: {
    assets: number;
    people: number;
    tags: number;
    places: number;
  };
};

export type AlbumAssetDetailProjection = {
  id: number;
  shortId: string;
  sourceName: string;
  sourceType: string;
  mediaType: string;
  title: string;
  caption: string | null;
  description: string | null;
  timestamp: string;
  latitude: number | null;
  longitude: number | null;
  camera: string | null;
  lens: string | null;
  apertureFNumber: number | null;
  shutterSpeedSeconds: number | null;
  focalLengthMm: number | null;
  iso: number | null;
  thumbnailUrl: string;
  originalUrl: string;
  people: PersonProjection[];
  tags: TagProjection[];
  faceRegions: Array<{
    name: string;
    left: number;
    top: number;
    right: number;
    bottom: number;
  }>;
};

type AlbumApiFilters = {
  selectedPersons: string[];
  selectedTags: string[];
};

function mapSelection(selection: ApiAlbumSelection): AlbumSelectionProjection {
  return {
    nodeKind: selection.node_kind,
    id: selection.id,
    sourceId: selection.source_id,
    sourceName: selection.source_name,
    sourceType: selection.source_type,
    parentId: selection.parent_id ?? null,
    name: selection.name,
    path: selection.path,
    assetCount: selection.asset_count,
    collectionType: selection.collection_type ?? null,
  };
}

function mapTreeNode(
  node: ApiAlbumFolderNode | ApiAlbumCollectionNode,
): AlbumTreeNodeProjection {
  return {
    id: node.id,
    sourceId: node.source_id,
    sourceName: node.source_name,
    sourceType: node.source_type,
    parentId: node.parent_id ?? null,
    name: node.name,
    path: node.path,
    childCount: node.child_count,
    assetCount: node.asset_count,
    collectionType: "collection_type" in node ? node.collection_type : null,
  };
}

function mapListing(
  response: ApiAlbumAssetListingResponse,
): AlbumAssetListingProjection {
  return {
    selection: mapSelection(response.selection),
    items: response.items.map((item) => ({
      id: item.id,
      shortId: item.short_id,
      timestamp: item.timestamp,
      mediaType: item.media_type,
      title: item.title,
      thumbnailUrl: resolveBackendUrl(item.thumbnail_url),
    })),
  };
}

function mapContext(response: ApiAlbumContextResponse): AlbumContextProjection {
  return {
    selection: mapSelection(response.selection),
    persons: response.persons.map((person) => ({
      id: String(person.id),
      name: person.name,
      role: person.path ?? null,
      assetCount: person.asset_count,
    })),
    tags: response.tags.map((tag) => ({
      id: String(tag.id),
      path: tag.path ?? tag.label,
      label: tag.label,
      assetCount: tag.asset_count,
    })),
    mapPoints: response.map_points.map((point) => ({
      id: point.id,
      label: point.label ?? null,
      latitude: point.latitude,
      longitude: point.longitude,
      assetCount: point.asset_count,
    })),
    assetContextsByAssetId: Object.fromEntries(
      response.asset_contexts.map((item) => [
        item.asset_id,
        {
          assetId: item.asset_id,
          personIds: item.person_ids.map(String),
          tagPaths: item.tag_paths,
          mapPointIds: item.map_point_ids,
        },
      ]),
    ),
    summaryCounts: response.summary_counts,
  };
}

function mapAssetDetail(
  response: ApiAlbumAssetDetailResponse,
): AlbumAssetDetailProjection {
  return {
    id: response.id,
    shortId: response.short_id,
    sourceName: response.source_name,
    sourceType: response.source_type,
    mediaType: response.media_type,
    title: response.title,
    caption: response.caption ?? null,
    description: response.description ?? null,
    timestamp: response.timestamp,
    latitude: response.latitude ?? null,
    longitude: response.longitude ?? null,
    camera: response.camera ?? null,
    lens: response.lens ?? null,
    apertureFNumber: response.aperture_f_number ?? null,
    shutterSpeedSeconds: response.shutter_speed_seconds ?? null,
    focalLengthMm: response.focal_length_mm ?? null,
    iso: response.iso ?? null,
    thumbnailUrl: resolveBackendUrl(response.thumbnail_url),
    originalUrl: resolveBackendUrl(response.original_url),
    people: response.people.map((person) => ({
      id: String(person.id),
      name: person.name,
      role: person.path ?? null,
    })),
    tags: response.tags.map((tag) => ({
      path: tag.path ?? tag.label,
      label: tag.label,
    })),
    faceRegions: response.face_regions,
  };
}

export const albumApi = {
  async getFolderTree(filters: AlbumApiFilters): Promise<AlbumTreeNodeProjection[]> {
    const response = await albumTransport.getFolderTree({
      personIds: filters.selectedPersons,
      tagPaths: filters.selectedTags,
    });

    return response.nodes.map(mapTreeNode);
  },

  async getCollectionTree(
    filters: AlbumApiFilters,
  ): Promise<AlbumTreeNodeProjection[]> {
    const response = await albumTransport.getCollectionTree({
      personIds: filters.selectedPersons,
      tagPaths: filters.selectedTags,
    });

    return response.nodes.map(mapTreeNode);
  },

  async getFolderListing(
    folderId: number,
    filters: AlbumApiFilters,
  ): Promise<AlbumAssetListingProjection> {
    return mapListing(
      await albumTransport.getFolderAssets(folderId, {
        personIds: filters.selectedPersons,
        tagPaths: filters.selectedTags,
      }),
    );
  },

  async getCollectionListing(
    collectionId: number,
    filters: AlbumApiFilters,
  ): Promise<AlbumAssetListingProjection> {
    return mapListing(
      await albumTransport.getCollectionAssets(collectionId, {
        personIds: filters.selectedPersons,
        tagPaths: filters.selectedTags,
      }),
    );
  },

  async getFolderContext(
    folderId: number,
    filters: AlbumApiFilters,
  ): Promise<AlbumContextProjection> {
    return mapContext(
      await albumTransport.getFolderContext(folderId, {
        personIds: filters.selectedPersons,
        tagPaths: filters.selectedTags,
      }),
    );
  },

  async getCollectionContext(
    collectionId: number,
    filters: AlbumApiFilters,
  ): Promise<AlbumContextProjection> {
    return mapContext(
      await albumTransport.getCollectionContext(collectionId, {
        personIds: filters.selectedPersons,
        tagPaths: filters.selectedTags,
      }),
    );
  },

  async getAssetDetail(assetId: number): Promise<AlbumAssetDetailProjection> {
    return mapAssetDetail(await albumTransport.getAssetDetail(assetId));
  },
};
