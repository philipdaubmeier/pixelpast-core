import type { ViewMode } from "../state/ui-state";

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
  activityScore: number;
  colorValue: "empty" | "low" | "medium" | "high";
  hasData: boolean;
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
  id: string;
  label: string;
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

export type ViewModeOption = {
  id: ViewMode;
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

export function getViewModeColorToken(
  options: ViewModeOption[],
  viewModeId: ViewMode,
): string {
  if (options.length === 0) {
    return viewColorTokens[0];
  }

  const viewIndex = options.findIndex((option) => option.id === viewModeId);
  const normalizedIndex = viewIndex >= 0 ? viewIndex : 0;

  return viewColorTokens[normalizedIndex % viewColorTokens.length];
}
