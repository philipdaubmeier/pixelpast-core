import type { DateRange, ViewModeOption } from "../projections/timeline";

export type ApiExplorationResponse = {
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
  days: Array<{
    date: string;
    event_count: number;
    asset_count: number;
    activity_score: number;
    color_value: "empty" | "low" | "medium" | "high";
    has_data: boolean;
    person_ids: number[];
    tag_paths: string[];
  }>;
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

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(buildApiUrl(path));

  if (!response.ok) {
    throw new Error(`Timeline API request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export const timelineTransport = {
  getExploration(): Promise<ApiExplorationResponse> {
    return requestJson<ApiExplorationResponse>("/exploration");
  },

  getDayContextRange(range: DateRange): Promise<ApiDayContextResponse> {
    return requestJson<ApiDayContextResponse>(
      `/days/context?start=${range.start}&end=${range.end}`,
    );
  },
};
