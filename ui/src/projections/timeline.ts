import type { ViewMode } from "../state/ui-state";

export type HeatmapDayProjection = {
  date: string;
  year: number;
  weekIndex: number;
  weekdayIndex: number;
  activityScore: number;
  colorValue: "empty" | "low" | "medium" | "high";
  hasData: boolean;
  eventCount: number;
  assetCount: number;
  personIds: string[];
  tagPaths: string[];
};

export type PersonProjection = {
  id: string;
  name: string;
  role: string;
};

export type TagProjection = {
  path: string;
  label: string;
};

export type MapPointProjection = {
  id: string;
  label: string;
  x: number;
  y: number;
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
