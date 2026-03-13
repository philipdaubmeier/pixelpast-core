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

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = (
    import.meta.env.VITE_PIXELPAST_API_BASE_URL ?? ""
  ).replace(/\/$/, "");

  if (configuredBaseUrl !== "") {
    return configuredBaseUrl;
  }

  if (import.meta.env.DEV && typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "";
}

const apiBaseUrl = resolveApiBaseUrl();

function buildApiUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
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
