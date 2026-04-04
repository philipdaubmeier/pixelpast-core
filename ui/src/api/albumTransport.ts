export type ApiAlbumAppliedFilters = {
  person_ids?: number[];
  person_group_ids?: number[];
  tag_paths?: string[];
};

export type ApiAlbumFolderNode = {
  id: number;
  source_id: number;
  source_name: string;
  source_type: string;
  parent_id?: number;
  name: string;
  path: string;
  child_count: number;
  asset_count: number;
  person_groups: ApiAlbumPersonGroupRelevance[];
};

export type ApiAlbumCollectionNode = ApiAlbumFolderNode & {
  collection_type: string;
};

export type ApiAlbumPersonGroupRelevance = {
  group_id: number;
  group_name: string;
  color_index?: number;
  matched_person_count: number;
  group_person_count: number;
  matched_asset_count: number;
  matched_creator_person_count: number;
};

export type ApiAlbumSelection = {
  node_kind: "folder" | "collection";
  id: number;
  source_id: number;
  source_name: string;
  source_type: string;
  parent_id?: number;
  name: string;
  path: string;
  asset_count: number;
  collection_type?: string;
};

export type ApiAlbumAssetItem = {
  id: number;
  short_id: string;
  timestamp: string;
  media_type: string;
  title: string;
  thumbnail_url: string;
};

export type ApiAlbumContextPerson = {
  id: number;
  name: string;
  path?: string;
  asset_count: number;
};

export type ApiAlbumContextTag = {
  id: number;
  label: string;
  path?: string;
  asset_count: number;
};

export type ApiAlbumContextMapPoint = {
  id: string;
  label?: string;
  latitude: number;
  longitude: number;
  asset_count: number;
};

export type ApiAlbumContextAssetItem = {
  asset_id: number;
  person_ids: number[];
  tag_paths: string[];
  map_point_ids: string[];
};

export type ApiAlbumContextResponse = {
  supported_filters: string[];
  applied_filters: ApiAlbumAppliedFilters;
  selection: ApiAlbumSelection;
  person_groups: ApiAlbumPersonGroupRelevance[];
  persons: ApiAlbumContextPerson[];
  tags: ApiAlbumContextTag[];
  map_points: ApiAlbumContextMapPoint[];
  asset_contexts: ApiAlbumContextAssetItem[];
  summary_counts: {
    assets: number;
    people: number;
    tags: number;
    places: number;
  };
};

export type ApiAlbumTreeResponse = {
  supported_filters: string[];
  applied_filters: ApiAlbumAppliedFilters;
  nodes: ApiAlbumFolderNode[];
};

export type ApiAlbumCollectionsTreeResponse = {
  supported_filters: string[];
  applied_filters: ApiAlbumAppliedFilters;
  nodes: ApiAlbumCollectionNode[];
};

export type ApiAlbumAssetListingResponse = {
  supported_filters: string[];
  applied_filters: ApiAlbumAppliedFilters;
  selection: ApiAlbumSelection;
  items: ApiAlbumAssetItem[];
};

export type ApiAlbumAssetDetailResponse = {
  id: number;
  short_id: string;
  source_id: number;
  source_name: string;
  source_type: string;
  media_type: string;
  title: string;
  creator?: string;
  preserved_filename?: string;
  caption?: string;
  description?: string;
  timestamp: string;
  latitude?: number;
  longitude?: number;
  camera?: string;
  lens?: string;
  aperture_f_number?: number;
  shutter_speed_seconds?: number;
  focal_length_mm?: number;
  iso?: number;
  thumbnail_url: string;
  original_url: string;
  tags: Array<{
    id: number;
    label: string;
    path?: string;
  }>;
  people: Array<{
    id: number;
    name: string;
    path?: string;
  }>;
  face_regions: Array<{
    name: string;
    left: number;
    top: number;
    right: number;
    bottom: number;
  }>;
};

type ApiAlbumTreeRequest = {
  personGroupIds: string[];
};

type ApiAlbumSelectionRequest = {
  personIds: string[];
  tagPaths: string[];
};

function normalizeConfiguredApiBaseUrl(value: string): string {
  const trimmedValue = value.replace(/\/$/, "");

  if (trimmedValue === "") {
    return "";
  }

  return trimmedValue.endsWith("/api") ? trimmedValue : `${trimmedValue}/api`;
}

const apiBaseUrl = normalizeConfiguredApiBaseUrl(
  import.meta.env.VITE_PIXELPAST_API_BASE_URL ?? "",
);

const backendBaseUrl =
  apiBaseUrl === "" ? "" : apiBaseUrl.replace(/\/api$/, "");

function buildApiUrl(path: string): string {
  if (apiBaseUrl !== "") {
    return `${apiBaseUrl}${path}`;
  }

  return `/api${path}`;
}

export function resolveBackendUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  if (backendBaseUrl !== "") {
    return `${backendBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
  }

  return path;
}

function buildQueryString(
  params: Record<string, string | number | Array<string | number> | undefined>,
): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        searchParams.append(key, String(item));
      }

      continue;
    }

    searchParams.set(key, String(value));
  }

  const serialized = searchParams.toString();
  return serialized === "" ? "" : `?${serialized}`;
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(buildApiUrl(path));

  if (!response.ok) {
    throw new Error(`Album API request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

function buildAlbumTreeFilterQuery(request: ApiAlbumTreeRequest): string {
  return buildQueryString({
    person_group_ids: request.personGroupIds,
  });
}

function buildAlbumSelectionFilterQuery(request: ApiAlbumSelectionRequest): string {
  return buildQueryString({
    person_ids: request.personIds,
    tag_paths: request.tagPaths,
  });
}

export const albumTransport = {
  getFolderTree(request: ApiAlbumTreeRequest): Promise<ApiAlbumTreeResponse> {
    return requestJson<ApiAlbumTreeResponse>(
      `/albums/folders${buildAlbumTreeFilterQuery(request)}`,
    );
  },

  getCollectionTree(
    request: ApiAlbumTreeRequest,
  ): Promise<ApiAlbumCollectionsTreeResponse> {
    return requestJson<ApiAlbumCollectionsTreeResponse>(
      `/albums/collections${buildAlbumTreeFilterQuery(request)}`,
    );
  },

  getFolderAssets(
    folderId: number,
    request: ApiAlbumSelectionRequest,
  ): Promise<ApiAlbumAssetListingResponse> {
    return requestJson<ApiAlbumAssetListingResponse>(
      `/albums/folders/${folderId}/assets${buildAlbumSelectionFilterQuery(request)}`,
    );
  },

  getCollectionAssets(
    collectionId: number,
    request: ApiAlbumSelectionRequest,
  ): Promise<ApiAlbumAssetListingResponse> {
    return requestJson<ApiAlbumAssetListingResponse>(
      `/albums/collections/${collectionId}/assets${buildAlbumSelectionFilterQuery(request)}`,
    );
  },

  getFolderContext(
    folderId: number,
    request: ApiAlbumSelectionRequest,
  ): Promise<ApiAlbumContextResponse> {
    return requestJson<ApiAlbumContextResponse>(
      `/albums/folders/${folderId}/context${buildAlbumSelectionFilterQuery(request)}`,
    );
  },

  getCollectionContext(
    collectionId: number,
    request: ApiAlbumSelectionRequest,
  ): Promise<ApiAlbumContextResponse> {
    return requestJson<ApiAlbumContextResponse>(
      `/albums/collections/${collectionId}/context${buildAlbumSelectionFilterQuery(request)}`,
    );
  },

  getAssetDetail(assetId: number): Promise<ApiAlbumAssetDetailResponse> {
    return requestJson<ApiAlbumAssetDetailResponse>(`/albums/assets/${assetId}`);
  },
};
