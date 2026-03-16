import type {
  DateRange,
  DayContextProjection,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../projections/timeline";
import type { PixelPastUiState } from "../state/ui-state";
import {
  timelineTransport,
  type ApiDayContextResponse,
  type ApiExplorationBootstrapResponse,
  type ApiExplorationGridResponse,
} from "./timelineTransport";

export type ExplorationBootstrapProjection = {
  range: DateRange;
  viewModes: ViewModeOption[];
  persons: PersonProjection[];
  tags: TagProjection[];
};

export type ExplorationGridProjection = {
  range: DateRange;
  heatmapDays: HeatmapDayProjection[];
};

export type ExplorationGridFilters = Pick<
  PixelPastUiState,
  "viewMode" | "selectedPersons" | "selectedTags"
>;

let explorationBootstrapPromise: Promise<ExplorationBootstrapProjection> | null =
  null;

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

function mapExplorationDay(
  day: ApiExplorationGridResponse["days"][number],
): HeatmapDayProjection {
  const parsedDate = createUtcDateFromIso(day.date);

  return {
    date: day.date,
    year: parsedDate.getUTCFullYear(),
    weekIndex: getWeekIndex(parsedDate),
    weekdayIndex: getWeekdayIndex(parsedDate),
    count: day.count,
    color: day.color,
    label: day.label,
  };
}

function mapPerson(
  person:
    | ApiExplorationBootstrapResponse["persons"][number]
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
    | ApiExplorationBootstrapResponse["tags"][number]
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
      latitude: point.latitude,
      longitude: point.longitude,
    })),
    summaryCounts: {
      events: day.summary_counts.events,
      assets: day.summary_counts.assets,
      places: day.summary_counts.places,
    },
  };
}

export const timelineApi = {
  async getExplorationBootstrap(): Promise<ExplorationBootstrapProjection> {
    if (explorationBootstrapPromise === null) {
      explorationBootstrapPromise = timelineTransport
        .getExplorationBootstrap()
        .then((bootstrap) => ({
          range: bootstrap.range,
          viewModes: bootstrap.view_modes,
          persons: bootstrap.persons.map(mapPerson),
          tags: bootstrap.tags.map(mapTag),
        }));
    }

    return explorationBootstrapPromise;
  },

  async getExplorationGrid(
    range: DateRange,
    filters: ExplorationGridFilters,
  ): Promise<ExplorationGridProjection> {
    const response = await timelineTransport.getExplorationGrid({
      start: range.start,
      end: range.end,
      viewMode: filters.viewMode,
      personIds: filters.selectedPersons,
      tagPaths: filters.selectedTags,
    });

    return {
      range: response.range,
      heatmapDays: response.days.map(mapExplorationDay),
    };
  },

  async getDayContextRange(
    range: DateRange,
  ): Promise<{
    range: DateRange;
    days: DayContextProjection[];
  }> {
    const response = await timelineTransport.getDayContextRange(range);

    return {
      range: response.range,
      days: response.days.map(mapDayContextDay),
    };
  },
};
