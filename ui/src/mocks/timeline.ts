import type {
  DayContextProjection,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../projections/timeline";

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function buildYearDays(year: number): HeatmapDayProjection[] {
  return Array.from({ length: 84 }, (_, index) => {
    const date = new Date(Date.UTC(year, 0, index + 1));
    const intensity = (index + year) % 4;
    const personIds = index % 9 === 0 ? ["anna"] : index % 7 === 0 ? ["milo"] : [];
    const tagPaths =
      index % 11 === 0
        ? ["travel/europe"]
        : index % 5 === 0
          ? ["people/family"]
          : [];

    return {
      date: toIsoDate(date),
      year,
      weekIndex: Math.floor(index / 7),
      weekdayIndex: index % 7,
      activityScore: intensity,
      colorValue:
        intensity === 0
          ? "empty"
          : intensity === 1
            ? "low"
            : intensity === 2
              ? "medium"
              : "high",
      hasData: intensity > 0,
      eventCount: intensity * 2,
      assetCount: intensity,
      personIds,
      tagPaths,
    };
  });
}

export const mockViewModes: ViewModeOption[] = [
  {
    id: "activity",
    label: "Activity",
    description: "Default heat intensity across all timeline sources.",
  },
  {
    id: "travel",
    label: "Travel",
    description: "Highlights movement-heavy and location-rich days.",
  },
  {
    id: "sports",
    label: "Sports",
    description: "Reserves the grid for workout and fitness projections.",
  },
  {
    id: "party_probability",
    label: "Social",
    description: "Placeholder derived view for future social-density signals.",
  },
];

export const mockPersons: PersonProjection[] = [
  { id: "anna", name: "Anna", role: "Family" },
  { id: "milo", name: "Milo", role: "Travel buddy" },
  { id: "luca", name: "Luca", role: "Work" },
];

export const mockTags: TagProjection[] = [
  { path: "people/family", label: "Family" },
  { path: "travel/europe", label: "Europe" },
  { path: "activity/outdoors", label: "Outdoors" },
];

export const mockHeatmapDays: HeatmapDayProjection[] = [
  ...buildYearDays(2023),
  ...buildYearDays(2024),
  ...buildYearDays(2025),
  ...buildYearDays(2026),
];

export const mockDayContexts: Record<string, DayContextProjection> = {
  "2026-01-09": {
    date: "2026-01-09",
    persons: [mockPersons[0], mockPersons[2]],
    tags: [mockTags[0], mockTags[2]],
    mapPoints: [
      { id: "berlin", label: "Berlin", x: 42, y: 36 },
      { id: "potsdam", label: "Potsdam", x: 54, y: 48 },
    ],
    summaryCounts: { events: 4, assets: 2, places: 2 },
  },
  "2026-01-16": {
    date: "2026-01-16",
    persons: [mockPersons[1]],
    tags: [mockTags[1]],
    mapPoints: [{ id: "venice", label: "Venice", x: 61, y: 59 }],
    summaryCounts: { events: 3, assets: 5, places: 1 },
  },
  "2026-01-23": {
    date: "2026-01-23",
    persons: [mockPersons[0], mockPersons[1]],
    tags: [mockTags[0], mockTags[1]],
    mapPoints: [
      { id: "munich", label: "Munich", x: 45, y: 69 },
      { id: "zurich", label: "Zurich", x: 34, y: 74 },
    ],
    summaryCounts: { events: 6, assets: 4, places: 2 },
  },
};
