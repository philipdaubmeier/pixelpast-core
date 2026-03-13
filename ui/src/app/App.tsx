import { startTransition, useEffect, useState } from "react";
import { timelineApi } from "../api/timeline";
import type {
  DayContextProjection,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../projections/timeline";
import { UiStateProvider, useUiState } from "../state/UiStateContext";
import { AppShell } from "./AppShell";

function AppBootstrap() {
  const { state } = useUiState();
  const [heatmapDays, setHeatmapDays] = useState<HeatmapDayProjection[]>([]);
  const [viewModes, setViewModes] = useState<ViewModeOption[]>([]);
  const [persons, setPersons] = useState<PersonProjection[]>([]);
  const [tags, setTags] = useState<TagProjection[]>([]);
  const [dayContextsByDate, setDayContextsByDate] = useState<
    Record<string, DayContextProjection>
  >({});
  const [activeDayContext, setActiveDayContext] =
    useState<DayContextProjection | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialShell() {
      const exploration = await timelineApi.getExploration();

      if (cancelled) {
        return;
      }

      startTransition(() => {
        setHeatmapDays(exploration.heatmapDays);
        setViewModes(exploration.viewModes);
        setPersons(exploration.persons);
        setTags(exploration.tags);
      });
    }

    void loadInitialShell();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (state.hoveredDate === null) {
      startTransition(() => {
        setActiveDayContext(null);
      });

      return;
    }

    const cachedDayContext = dayContextsByDate[state.hoveredDate];
    if (cachedDayContext) {
      startTransition(() => {
        setActiveDayContext(cachedDayContext);
      });

      return;
    }

    let cancelled = false;

    async function loadDayContext() {
      const nextContext = await timelineApi.getDayContext(state.hoveredDate);

      if (cancelled) {
        return;
      }

      startTransition(() => {
        setActiveDayContext(nextContext);
        if (nextContext !== null) {
          setDayContextsByDate((currentValue) => ({
            ...currentValue,
            [nextContext.date]: nextContext,
          }));
        }
      });
    }

    void loadDayContext();

    return () => {
      cancelled = true;
    };
  }, [dayContextsByDate, state.hoveredDate]);

  return (
    <AppShell
      heatmapDays={heatmapDays}
      viewModes={viewModes}
      persons={persons}
      tags={tags}
      dayContextsByDate={dayContextsByDate}
      activeDayContext={activeDayContext}
    />
  );
}

export function App() {
  return (
    <UiStateProvider>
      <AppBootstrap />
    </UiStateProvider>
  );
}
