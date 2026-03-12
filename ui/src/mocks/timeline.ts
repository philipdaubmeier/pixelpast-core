import type {
  DayContextProjection,
  HeatmapDayProjection,
  MapPointProjection,
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../projections/timeline";

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function createUtcDate(year: number, month: number, day: number): Date {
  return new Date(Date.UTC(year, month, day));
}

function getWeekdayIndex(date: Date): number {
  return (date.getUTCDay() + 6) % 7;
}

function getDaysInYear(year: number): number {
  const start = createUtcDate(year, 0, 1);
  const end = createUtcDate(year + 1, 0, 1);
  return Math.round((end.getTime() - start.getTime()) / 86_400_000);
}

function getWeekIndex(date: Date, startOfYear: Date): number {
  const startWeekday = getWeekdayIndex(startOfYear);
  const alignedStart = createUtcDate(
    startOfYear.getUTCFullYear(),
    startOfYear.getUTCMonth(),
    startOfYear.getUTCDate() - startWeekday,
  );

  return Math.floor((date.getTime() - alignedStart.getTime()) / 604_800_000);
}

function getColorValue(
  activityScore: number,
): HeatmapDayProjection["colorValue"] {
  if (activityScore <= 0) {
    return "empty";
  }

  if (activityScore < 35) {
    return "low";
  }

  if (activityScore < 70) {
    return "medium";
  }

  return "high";
}

function buildYearDays(year: number): HeatmapDayProjection[] {
  const startOfYear = createUtcDate(year, 0, 1);
  const daysInYear = getDaysInYear(year);

  return Array.from({ length: daysInYear }, (_, index) => {
    const date = createUtcDate(year, 0, index + 1);
    const seasonalWave = (Math.sin((index / daysInYear) * Math.PI * 4) + 1) / 2;
    const weeklyPulse = index % 7 === 5 || index % 7 === 6 ? 24 : 0;
    const travelPulse = index % 61 < 5 ? 18 : 0;
    const mediaPulse = index % 29 === 0 ? 12 : 0;
    const activityScore = Math.min(
      100,
      Math.round(seasonalWave * 52 + weeklyPulse + travelPulse + mediaPulse),
    );
    const eventCount = Math.round(activityScore / 18);
    const assetCount = Math.round(activityScore / 24);
    const personIds =
      index % 61 < 5
        ? ["anna", "milo"]
        : index % 17 === 0
          ? ["anna"]
          : index % 13 === 0
            ? ["luca"]
            : [];
    const tagPaths =
      index % 61 < 5
        ? ["travel/europe"]
        : index % 11 === 0
          ? ["people/family"]
          : index % 19 === 0
            ? ["activity/outdoors"]
            : [];

    return {
      date: toIsoDate(date),
      year,
      weekIndex: getWeekIndex(date, startOfYear),
      weekdayIndex: getWeekdayIndex(date),
      activityScore,
      colorValue: getColorValue(activityScore),
      hasData: activityScore > 0,
      eventCount,
      assetCount,
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

const personById = new Map(
  mockPersons.map((person) => [person.id, person] satisfies [string, PersonProjection]),
);
const tagByPath = new Map(
  mockTags.map((tag) => [tag.path, tag] satisfies [string, TagProjection]),
);
const mapLabels = [
  "Berlin",
  "Potsdam",
  "Venice",
  "Munich",
  "Zurich",
  "Prague",
  "Hamburg",
  "Leipzig",
];

function createMapPoints(day: HeatmapDayProjection): MapPointProjection[] {
  if (!day.hasData) {
    return [];
  }

  const pointCount =
    day.tagPaths.some((tagPath) => tagPath.startsWith("travel/"))
      ? 2
      : day.personIds.length > 0
        ? 1
        : 0;

  return Array.from({ length: pointCount }, (_, index) => {
    const labelIndex =
      (day.weekIndex + day.weekdayIndex + day.year + index) % mapLabels.length;
    const x = 18 + ((day.weekIndex * 11 + index * 17) % 58);
    const y = 22 + ((day.weekdayIndex * 13 + day.year + index * 19) % 52);

    return {
      id: `${day.date}-point-${index + 1}`,
      label: mapLabels[labelIndex],
      x,
      y,
    };
  });
}

function buildDayContext(day: HeatmapDayProjection): DayContextProjection {
  const persons = day.personIds
    .map((personId) => personById.get(personId))
    .filter((person): person is PersonProjection => person !== undefined);
  const tags = day.tagPaths
    .map((tagPath) => tagByPath.get(tagPath))
    .filter((tag): tag is TagProjection => tag !== undefined);
  const mapPoints = createMapPoints(day);

  return {
    date: day.date,
    persons,
    tags,
    mapPoints,
    summaryCounts: {
      events: day.eventCount,
      assets: day.assetCount,
      places: mapPoints.length,
    },
  };
}

export const mockHeatmapDays: HeatmapDayProjection[] = [
  ...buildYearDays(2021),
  ...buildYearDays(2022),
  ...buildYearDays(2023),
  ...buildYearDays(2024),
  ...buildYearDays(2025),
  ...buildYearDays(2026),
];

export const mockDayContexts: Record<string, DayContextProjection> =
  Object.fromEntries(
    mockHeatmapDays.map((day) => [day.date, buildDayContext(day)]),
  );
