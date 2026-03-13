import type {
  DayContextProjection,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../projections/timeline";

type ExplorationBootstrapProjection = {
  heatmapDays: HeatmapDayProjection[];
  viewModes: ViewModeOption[];
  persons: PersonProjection[];
  tags: TagProjection[];
};

type ApiExplorationResponse = {
  range: {
    start: string;
    end: string;
  };
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
    color_value: HeatmapDayProjection["colorValue"];
    has_data: boolean;
    person_ids: number[];
    tag_paths: string[];
  }>;
};

type ApiDayContextResponse = {
  range: {
    start: string;
    end: string;
  };
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

const apiBaseUrl = (import.meta.env.VITE_PIXELPAST_API_BASE_URL ?? "").replace(
  /\/$/,
  "",
);
let explorationBootstrapPromise: Promise<ExplorationBootstrapProjection> | null =
  null;

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

function createUtcDateFromIso(date: string): Date {
  return new Date(`${date}T00:00:00Z`);
}

function getWeekdayIndex(date: Date): number {
  return (date.getUTCDay() + 6) % 7;
}

function getWeekIndex(date: Date): number {
  const startOfYear = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const startWeekday = getWeekdayIndex(startOfYear);
  const alignedStart = new Date(
    Date.UTC(
      startOfYear.getUTCFullYear(),
      startOfYear.getUTCMonth(),
      startOfYear.getUTCDate() - startWeekday,
    ),
  );

  return Math.floor((date.getTime() - alignedStart.getTime()) / 604_800_000);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function projectLongitude(longitude: number): number {
  return clamp(((longitude + 180) / 360) * 100, 8, 92);
}

function projectLatitude(latitude: number): number {
  return clamp(((90 - latitude) / 180) * 100, 10, 90);
}

function mapExplorationDay(day: ApiExplorationResponse["days"][number]): HeatmapDayProjection {
  const parsedDate = createUtcDateFromIso(day.date);

  return {
    date: day.date,
    year: parsedDate.getUTCFullYear(),
    weekIndex: getWeekIndex(parsedDate),
    weekdayIndex: getWeekdayIndex(parsedDate),
    activityScore: day.activity_score,
    colorValue: day.color_value,
    hasData: day.has_data,
    eventCount: day.event_count,
    assetCount: day.asset_count,
    personIds: day.person_ids.map(String),
    tagPaths: day.tag_paths,
  };
}

function mapPerson(
  person:
    | ApiExplorationResponse["persons"][number]
    | ApiDayContextResponse["days"][number]["persons"][number],
): PersonProjection {
  return {
    id: String(person.id),
    name: person.name,
    role: person.role,
  };
}

function mapTag(
  tag:
    | ApiExplorationResponse["tags"][number]
    | ApiDayContextResponse["days"][number]["tags"][number],
): TagProjection {
  return {
    path: tag.path,
    label: tag.label,
  };
}

function mapDayContextDay(
  day: ApiDayContextResponse["days"][number],
): DayContextProjection {
  return {
    date: day.date,
    persons: day.persons.map(mapPerson),
    tags: day.tags.map(mapTag),
    mapPoints: day.map_points.map((point) => ({
      id: point.id,
      label: point.label,
      x: projectLongitude(point.longitude),
      y: projectLatitude(point.latitude),
    })),
    summaryCounts: {
      events: day.summary_counts.events,
      assets: day.summary_counts.assets,
      places: day.summary_counts.places,
    },
  };
}

export const timelineApi = {
  async getExploration(): Promise<ExplorationBootstrapProjection> {
    if (explorationBootstrapPromise === null) {
      explorationBootstrapPromise = requestJson<ApiExplorationResponse>(
        "/exploration",
      ).then((response) => ({
        heatmapDays: response.days.map(mapExplorationDay),
        viewModes: response.view_modes,
        persons: response.persons.map(mapPerson),
        tags: response.tags.map(mapTag),
      }));
    }

    return explorationBootstrapPromise;
  },

  async getDayContext(date: string | null): Promise<DayContextProjection | null> {
    if (date === null) {
      return null;
    }

    const response = await requestJson<ApiDayContextResponse>(
      `/days/context?start=${date}&end=${date}`,
    );
    const [dayContext] = response.days;

    return dayContext ? mapDayContextDay(dayContext) : null;
  },
};
