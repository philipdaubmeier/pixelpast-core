import type {
  DateRange,
  DayContextProjection,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../projections/timeline";
import {
  timelineTransport,
  type ApiDayContextResponse,
  type ApiExplorationResponse,
} from "./timelineTransport";

export type ExplorationBootstrapProjection = {
  range: DateRange;
  heatmapDays: HeatmapDayProjection[];
  viewModes: ViewModeOption[];
  persons: PersonProjection[];
  tags: TagProjection[];
};

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
  day: ApiExplorationResponse["days"][number],
): HeatmapDayProjection {
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
  async getExploration(): Promise<ExplorationBootstrapProjection> {
    if (explorationBootstrapPromise === null) {
      explorationBootstrapPromise = timelineTransport.getExploration().then(
        (response) => ({
          range: response.range,
          heatmapDays: response.days.map(mapExplorationDay),
          viewModes: response.view_modes,
          persons: response.persons.map(mapPerson),
          tags: response.tags.map(mapTag),
        }),
      );
    }

    return explorationBootstrapPromise;
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
