import type { PixelPastUiState, ViewMode } from "../state/ui-state";
import type {
  DayContextProjection,
  HeatmapDayProjection,
  MapPointProjection,
  PersonProjection,
  TagProjection,
} from "./timeline";

type SummaryCounts = DayContextProjection["summaryCounts"];
type HeatmapColorValue = HeatmapDayProjection["colorValue"];

type ExplorationProjectionInput = {
  heatmapDays: HeatmapDayProjection[];
  dayContextsByDate: Record<string, DayContextProjection>;
  activeDayContext: DayContextProjection | null;
  allPersons: PersonProjection[];
  allTags: TagProjection[];
  state: Pick<
    PixelPastUiState,
    "hoveredDate" | "viewMode" | "selectedPersons" | "selectedTags"
  >;
};

export type HeatmapDayRenderProjection = HeatmapDayProjection & {
  renderColorValue: HeatmapColorValue;
  isDimmed: boolean;
  hasPersistentFilters: boolean;
  matchesPersistentFilters: boolean;
};

export type PersonPanelItemProjection = PersonProjection & {
  isSelected: boolean;
  isHoverHighlighted: boolean;
};

export type TagPanelItemProjection = TagProjection & {
  isSelected: boolean;
  isHoverHighlighted: boolean;
};

export type ExplorationProjection = {
  gridDays: HeatmapDayRenderProjection[];
  visiblePersons: PersonPanelItemProjection[];
  visibleTags: TagPanelItemProjection[];
  selectedPersons: PersonProjection[];
  selectedTags: TagProjection[];
  hasPersistentFilters: boolean;
  matchingDayCount: number;
  mapPoints: MapPointProjection[];
  mapSummary: SummaryCounts | null;
};

function uniqueBy<T>(items: T[], getKey: (item: T) => string): T[] {
  const seen = new Set<string>();

  return items.filter((item) => {
    const key = getKey(item);

    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}

function matchesTagSelection(dayTagPath: string, selectedTagPath: string): boolean {
  return (
    dayTagPath === selectedTagPath ||
    dayTagPath.startsWith(`${selectedTagPath}/`) ||
    selectedTagPath.startsWith(`${dayTagPath}/`)
  );
}

function matchesPersistentFilters(
  day: HeatmapDayProjection,
  selectedPersons: string[],
  selectedTags: string[],
): boolean {
  const personMatch =
    selectedPersons.length === 0 ||
    selectedPersons.some((personId) => day.personIds.includes(personId));
  const tagMatch =
    selectedTags.length === 0 ||
    selectedTags.some((selectedTag) =>
      day.tagPaths.some((tagPath) => matchesTagSelection(tagPath, selectedTag)),
    );

  return personMatch && tagMatch;
}

function getViewModeColorValue(
  day: HeatmapDayProjection,
  viewMode: ViewMode,
): HeatmapColorValue {
  switch (viewMode) {
    case "activity":
      return day.colorValue;
    case "travel":
      if (day.tagPaths.some((tagPath) => tagPath.startsWith("travel/"))) {
        return "high";
      }

      if (day.personIds.length > 0) {
        return "medium";
      }

      return day.activityScore >= 55 ? "low" : "empty";
    case "sports":
      if (day.tagPaths.some((tagPath) => tagPath.startsWith("activity/"))) {
        return "high";
      }

      if (day.activityScore >= 78) {
        return "medium";
      }

      return day.activityScore >= 60 ? "low" : "empty";
    case "party_probability":
      if (day.personIds.length >= 2) {
        return "high";
      }

      if (day.personIds.length === 1) {
        return "medium";
      }

      return day.tagPaths.some((tagPath) => tagPath.startsWith("people/"))
        ? "low"
        : "empty";
  }
}

function promoteColorValue(colorValue: HeatmapColorValue): HeatmapColorValue {
  switch (colorValue) {
    case "empty":
      return "low";
    case "low":
      return "medium";
    case "medium":
      return "high";
    case "high":
      return "high";
  }
}

function createFallbackPerson(id: string): PersonProjection {
  return {
    id,
    name: id,
    role: "URL selection",
  };
}

function createFallbackTag(path: string): TagProjection {
  return {
    path,
    label: path,
  };
}

function resolveSelectedPersons(
  selectedPersons: string[],
  allPersons: PersonProjection[],
): PersonProjection[] {
  const personById = new Map(allPersons.map((person) => [person.id, person]));

  return selectedPersons.map((personId) => {
    return personById.get(personId) ?? createFallbackPerson(personId);
  });
}

function resolveSelectedTags(
  selectedTags: string[],
  allTags: TagProjection[],
): TagProjection[] {
  const tagByPath = new Map(allTags.map((tag) => [tag.path, tag]));

  return selectedTags.map((tagPath) => {
    return tagByPath.get(tagPath) ?? createFallbackTag(tagPath);
  });
}

function buildVisiblePersons(
  selectedPersons: PersonProjection[],
  hoveredPersons: PersonProjection[],
  allPersons: PersonProjection[],
): PersonPanelItemProjection[] {
  const selectedPersonIds = new Set(
    selectedPersons.map((person) => person.id),
  );
  const hoveredPersonIds = new Set(hoveredPersons.map((person) => person.id));

  return uniqueBy(
    [...selectedPersons, ...hoveredPersons, ...allPersons],
    (person) => person.id,
  ).map((person) => ({
    ...person,
    isSelected: selectedPersonIds.has(person.id),
    isHoverHighlighted: hoveredPersonIds.has(person.id),
  }));
}

function buildVisibleTags(
  selectedTags: TagProjection[],
  hoveredTags: TagProjection[],
  allTags: TagProjection[],
): TagPanelItemProjection[] {
  const selectedTagPaths = new Set(selectedTags.map((tag) => tag.path));
  const hoveredTagPaths = new Set(hoveredTags.map((tag) => tag.path));

  return uniqueBy(
    [...selectedTags, ...hoveredTags, ...allTags],
    (tag) => tag.path,
  ).map((tag) => ({
    ...tag,
    isSelected: selectedTagPaths.has(tag.path),
    isHoverHighlighted: hoveredTagPaths.has(tag.path),
  }));
}

function buildGridDays(
  heatmapDays: HeatmapDayProjection[],
  viewMode: ViewMode,
  selectedPersons: string[],
  selectedTags: string[],
): HeatmapDayRenderProjection[] {
  const hasPersistentFilters =
    selectedPersons.length > 0 || selectedTags.length > 0;

  return heatmapDays.map((day) => {
    const baseColorValue = getViewModeColorValue(day, viewMode);
    const matchesFilters = hasPersistentFilters
      ? matchesPersistentFilters(day, selectedPersons, selectedTags)
      : true;

    if (!hasPersistentFilters) {
      return {
        ...day,
        renderColorValue: baseColorValue,
        isDimmed: false,
        hasPersistentFilters: false,
        matchesPersistentFilters: true,
      };
    }

    return {
      ...day,
      renderColorValue: matchesFilters
        ? promoteColorValue(baseColorValue)
        : day.hasData
          ? "low"
          : "empty",
      isDimmed: !matchesFilters,
      hasPersistentFilters: true,
      matchesPersistentFilters: matchesFilters,
    };
  });
}

function buildMapProjection(
  hoveredDate: string | null,
  activeDayContext: DayContextProjection | null,
  gridDays: HeatmapDayRenderProjection[],
  dayContextsByDate: Record<string, DayContextProjection>,
): {
  mapPoints: MapPointProjection[];
  mapSummary: SummaryCounts | null;
} {
  if (hoveredDate !== null) {
    return {
      mapPoints: activeDayContext?.mapPoints ?? [],
      mapSummary: activeDayContext?.summaryCounts ?? null,
    };
  }

  const matchingContexts = gridDays
    .filter((day) => day.hasPersistentFilters && day.matchesPersistentFilters)
    .map((day) => dayContextsByDate[day.date])
    .filter((context): context is DayContextProjection => context !== undefined);

  if (matchingContexts.length === 0) {
    return {
      mapPoints: [],
      mapSummary: null,
    };
  }

  const mapPoints = uniqueBy(
    matchingContexts.flatMap((context) => context.mapPoints),
    (point) => point.label,
  ).slice(0, 12);
  const mapSummary = matchingContexts.reduce<SummaryCounts>(
    (summary, context) => ({
      events: summary.events + context.summaryCounts.events,
      assets: summary.assets + context.summaryCounts.assets,
      places: summary.places + context.summaryCounts.places,
    }),
    {
      events: 0,
      assets: 0,
      places: 0,
    },
  );

  return {
    mapPoints,
    mapSummary,
  };
}

export function buildExplorationProjection({
  heatmapDays,
  dayContextsByDate,
  activeDayContext,
  allPersons,
  allTags,
  state,
}: ExplorationProjectionInput): ExplorationProjection {
  const selectedPersons = resolveSelectedPersons(
    state.selectedPersons,
    allPersons,
  );
  const selectedTags = resolveSelectedTags(state.selectedTags, allTags);
  const hoveredPersons =
    state.hoveredDate !== null ? activeDayContext?.persons ?? [] : [];
  const hoveredTags =
    state.hoveredDate !== null ? activeDayContext?.tags ?? [] : [];
  const gridDays = buildGridDays(
    heatmapDays,
    state.viewMode,
    state.selectedPersons,
    state.selectedTags,
  );
  const matchingDayCount = gridDays.filter(
    (day) => day.matchesPersistentFilters && day.hasData,
  ).length;
  const { mapPoints, mapSummary } = buildMapProjection(
    state.hoveredDate,
    activeDayContext,
    gridDays,
    dayContextsByDate,
  );

  return {
    gridDays,
    visiblePersons: buildVisiblePersons(
      selectedPersons,
      hoveredPersons,
      allPersons,
    ),
    visibleTags: buildVisibleTags(selectedTags, hoveredTags, allTags),
    selectedPersons,
    selectedTags,
    hasPersistentFilters:
      state.selectedPersons.length > 0 || state.selectedTags.length > 0,
    matchingDayCount,
    mapPoints,
    mapSummary,
  };
}
