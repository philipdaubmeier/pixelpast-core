import type { GridView } from "../state/ui-state";

export type DateRange = {
  start: string;
  end: string;
};

export type HeatmapDayProjection = {
  date: string;
  year: number;
  weekIndex: number;
  weekdayIndex: number;
  count: number;
  color: "empty" | "low" | "medium" | "high" | `#${string}`;
  label?: string;
};

export type PersonProjection = {
  id: string;
  name: string;
  role: string | null;
};

export type TagProjection = {
  path: string;
  label: string;
};

export type MapPointProjection = {
  id: string | null;
  label: string | null;
  latitude: number;
  longitude: number;
};

export type DayContextProjection = {
  date: string;
  persons: PersonProjection[];
  tags: TagProjection[];
  mapPoints: MapPointProjection[];
  summaryCounts: {
    events: number;
    assets: number;
    places: number;
  };
};

export type GridViewOption = {
  id: GridView;
  label: string;
  description: string;
};

export const viewColorTokens = [
  "var(--pp-grid-viewcolor1)",
  "var(--pp-grid-viewcolor2)",
  "var(--pp-grid-viewcolor3)",
  "var(--pp-grid-viewcolor4)",
  "var(--pp-grid-viewcolor5)",
] as const;

export function getGridViewColorToken(
  options: GridViewOption[],
  gridViewId: GridView,
): string {
  if (options.length === 0) {
    return viewColorTokens[0];
  }

  const viewIndex = options.findIndex((option) => option.id === gridViewId);
  const normalizedIndex = viewIndex >= 0 ? viewIndex : 0;

  return viewColorTokens[normalizedIndex % viewColorTokens.length];
}
