import { startTransition, useEffect, useState } from "react";
import { timelineApi } from "../api/timeline";
import type {
  DayContextProjection,
  HeatmapDayProjection,
  ViewModeOption,
} from "../projections/timeline";
import { UiStateProvider, useUiState } from "../state/UiStateContext";
import { AppShell } from "./AppShell";

function AppBootstrap() {
  const { state } = useUiState();
  const [heatmapDays, setHeatmapDays] = useState<HeatmapDayProjection[]>([]);
  const [viewModes, setViewModes] = useState<ViewModeOption[]>([]);
  const [activeDayContext, setActiveDayContext] =
    useState<DayContextProjection | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialShell() {
      const [days, modes] = await Promise.all([
        timelineApi.listHeatmapDays(),
        timelineApi.listViewModes(),
      ]);

      if (cancelled) {
        return;
      }

      startTransition(() => {
        setHeatmapDays(days);
        setViewModes(modes);
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

    let cancelled = false;

    async function loadDayContext() {
      const nextContext = await timelineApi.getDayContext(state.hoveredDate);

      if (cancelled) {
        return;
      }

      startTransition(() => {
        setActiveDayContext(nextContext);
      });
    }

    void loadDayContext();

    return () => {
      cancelled = true;
    };
  }, [state.hoveredDate]);

  return (
    <AppShell
      heatmapDays={heatmapDays}
      viewModes={viewModes}
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
