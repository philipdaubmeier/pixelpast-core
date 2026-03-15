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
