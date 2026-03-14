import type { DateRange, ViewModeOption } from "../projections/timeline";

export type ApiExplorationBootstrapResponse = {
  range: DateRange;
  view_modes: Array<{
    id: ViewModeOption["id"];
    label: string;
    description: string;
  }>;
  persons: Array<{
    id: number;
    name: string;
    role: string | null;
  }>;
  tags: Array<{
    path: string;
    label: string;
  }>;
};

export type ApiExplorationGridResponse = {
  range: DateRange;
  days: Array<{
    date: string;
    activity_score: number;
    color_value: "empty" | "low" | "medium" | "high";
    has_data: boolean;
  }>;
};

export type ApiExplorationGridRequest = {
  start?: string;
  end?: string;
  viewMode: ViewModeOption["id"];
  personIds: string[];
  tagPaths: string[];
  locationGeometry?: string;
  distanceLatitude?: number;
  distanceLongitude?: number;
  distanceRadiusMeters?: number;
  filenameQuery?: string;
};

export type ApiDayContextResponse = {
  range: DateRange;
  days: Array<{
    date: string;
    persons: Array<{
      id: number;
      name: string;
      role: string | null;
    }>;
    tags: Array<{
      path: string;
      label: string;
    }>;
    map_points: Array<{
      id: string;
      label: string;
      latitude: number;
      longitude: number;
    }>;
    summary_counts: {
      events: number;
      assets: number;
      places: number;
    };
  }>;
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

function buildApiUrl(path: string): string {
  if (apiBaseUrl !== "") {
    return `${apiBaseUrl}${path}`;
  }

  return `/api${path}`;
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
    throw new Error(`Timeline API request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export const timelineTransport = {
  getExplorationBootstrap(): Promise<ApiExplorationBootstrapResponse> {
    return requestJson<ApiExplorationBootstrapResponse>("/exploration/bootstrap");
  },

  getExplorationGrid(
    request: ApiExplorationGridRequest,
  ): Promise<ApiExplorationGridResponse> {
    return requestJson<ApiExplorationGridResponse>(
      `/exploration${buildQueryString({
        start: request.start,
        end: request.end,
        view_mode: request.viewMode,
        person_ids: request.personIds,
        tag_paths: request.tagPaths,
        location_geometry: request.locationGeometry,
        distance_latitude: request.distanceLatitude,
        distance_longitude: request.distanceLongitude,
        distance_radius_meters: request.distanceRadiusMeters,
        filename_query: request.filenameQuery,
      })}`,
    );
  },

  getDayContextRange(range: DateRange): Promise<ApiDayContextResponse> {
    return requestJson<ApiDayContextResponse>(
      `/days/context?start=${range.start}&end=${range.end}`,
    );
  },
};
