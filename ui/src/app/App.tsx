import { startTransition, useEffect, useRef, useState } from "react";
import { timelineApi } from "../api/timeline";
import type {
  DateRange,
  DayContextProjection,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../projections/timeline";
import { UiStateProvider, useUiState } from "../state/UiStateContext";
import { AppShell } from "./AppShell";

type ShellLoadState = "loading" | "ready" | "error";
type GridLoadState = "loading" | "ready" | "error";
type HoverContextStatus = "idle" | "loading" | "ready" | "error";

function isDateInRange(date: string, range: DateRange): boolean {
  return range.start <= date && date <= range.end;
}

function isRangeLoaded(range: DateRange, cachedRanges: DateRange[]): boolean {
  return cachedRanges.some(
    (cachedRange) =>
      cachedRange.start <= range.start && cachedRange.end >= range.end,
  );
}

function appendRange(ranges: DateRange[], nextRange: DateRange): DateRange[] {
  if (
    ranges.some(
      (range) =>
        range.start === nextRange.start && range.end === nextRange.end,
    )
  ) {
    return ranges;
  }

  return [...ranges, nextRange];
}

function removeRange(ranges: DateRange[], targetRange: DateRange): DateRange[] {
  return ranges.filter(
    (range) =>
      range.start !== targetRange.start || range.end !== targetRange.end,
  );
}

function resolveHoverContextStatus(
  hoveredDate: string | null,
  dayContextsByDate: Record<string, DayContextProjection>,
  loadingRanges: DateRange[],
  failedRanges: DateRange[],
): HoverContextStatus {
  if (hoveredDate === null) {
    return "idle";
  }

  if (dayContextsByDate[hoveredDate] !== undefined) {
    return "ready";
  }

  if (failedRanges.some((range) => isDateInRange(hoveredDate, range))) {
    return "error";
  }

  if (loadingRanges.some((range) => isDateInRange(hoveredDate, range))) {
    return "loading";
  }

  return "loading";
}

function AppBootstrap() {
  const { state, setHoveredDate } = useUiState();
  const isMountedRef = useRef(true);
  const latestGridRequestIdRef = useRef(0);
  const [shellState, setShellState] = useState<ShellLoadState>("loading");
  const [shellError, setShellError] = useState<string | null>(null);
  const [gridState, setGridState] = useState<GridLoadState>("loading");
  const [gridError, setGridError] = useState<string | null>(null);
  const [explorationRange, setExplorationRange] = useState<DateRange | null>(null);
  const [heatmapDays, setHeatmapDays] = useState<HeatmapDayProjection[]>([]);
  const [viewModes, setViewModes] = useState<ViewModeOption[]>([]);
  const [persons, setPersons] = useState<PersonProjection[]>([]);
  const [tags, setTags] = useState<TagProjection[]>([]);
  const [visibleRanges, setVisibleRanges] = useState<DateRange[]>([]);
  const [dayContextsByDate, setDayContextsByDate] = useState<
    Record<string, DayContextProjection>
  >({});
  const [loadedDayContextRanges, setLoadedDayContextRanges] = useState<DateRange[]>(
    [],
  );
  const [loadingDayContextRanges, setLoadingDayContextRanges] = useState<
    DateRange[]
  >([]);
  const [failedDayContextRanges, setFailedDayContextRanges] = useState<DateRange[]>(
    [],
  );
  const [hoverContextError, setHoverContextError] = useState<string | null>(null);

  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    async function loadInitialShell() {
      try {
        const bootstrap = await timelineApi.getExplorationBootstrap();

        if (!isMountedRef.current) {
          return;
        }

        startTransition(() => {
          setExplorationRange(bootstrap.range);
          setViewModes(bootstrap.viewModes);
          setPersons(bootstrap.persons);
          setTags(bootstrap.tags);
          setShellState("ready");
          setShellError(null);
        });
      } catch (error) {
        if (!isMountedRef.current) {
          return;
        }

        startTransition(() => {
          setShellState("error");
          setShellError(
            error instanceof Error
              ? error.message
              : "Unable to load the exploration shell.",
          );
        });
      }
    }

    void loadInitialShell();
  }, []);

  useEffect(() => {
    if (shellState !== "ready" || explorationRange === null) {
      return;
    }

    const requestId = latestGridRequestIdRef.current + 1;
    latestGridRequestIdRef.current = requestId;
    setHoveredDate(null);

    startTransition(() => {
      setGridState("loading");
      setGridError(null);
    });

    void (async () => {
      try {
        const grid = await timelineApi.getExplorationGrid(explorationRange, {
          viewMode: state.viewMode,
          selectedPersons: state.selectedPersons,
          selectedTags: state.selectedTags,
        });

        if (
          !isMountedRef.current ||
          latestGridRequestIdRef.current !== requestId
        ) {
          return;
        }

        startTransition(() => {
          setHeatmapDays(grid.heatmapDays);
          setGridState("ready");
          setGridError(null);
        });
      } catch (error) {
        if (
          !isMountedRef.current ||
          latestGridRequestIdRef.current !== requestId
        ) {
          return;
        }

        startTransition(() => {
          setGridState("error");
          setGridError(
            error instanceof Error
              ? error.message
              : "Unable to load the filtered exploration grid.",
          );
        });
      }
    })();
  }, [
    explorationRange,
    shellState,
    state.selectedPersons,
    state.selectedTags,
    state.viewMode,
  ]);

  useEffect(() => {
    if (shellState !== "ready" || visibleRanges.length === 0) {
      return;
    }

    const rangesToLoad = visibleRanges.filter(
      (range) =>
        !isRangeLoaded(range, loadedDayContextRanges) &&
        !isRangeLoaded(range, loadingDayContextRanges) &&
        !isRangeLoaded(range, failedDayContextRanges),
    );
    if (rangesToLoad.length === 0) {
      return;
    }

    for (const range of rangesToLoad) {
      startTransition(() => {
        setLoadingDayContextRanges((currentValue) =>
          appendRange(currentValue, range),
        );
        setFailedDayContextRanges((currentValue) =>
          removeRange(currentValue, range),
        );
      });

      void (async () => {
        try {
          const response = await timelineApi.getDayContextRange(range);

          if (!isMountedRef.current) {
            return;
          }

          startTransition(() => {
            setDayContextsByDate((currentValue) => {
              const nextValue = { ...currentValue };

              for (const dayContext of response.days) {
                nextValue[dayContext.date] = dayContext;
              }

              return nextValue;
            });
            setLoadedDayContextRanges((currentValue) =>
              appendRange(currentValue, response.range),
            );
            setLoadingDayContextRanges((currentValue) =>
              removeRange(currentValue, range),
            );
            setHoverContextError(null);
          });
        } catch (error) {
          if (!isMountedRef.current) {
            return;
          }

          startTransition(() => {
            setLoadingDayContextRanges((currentValue) =>
              removeRange(currentValue, range),
            );
            setFailedDayContextRanges((currentValue) =>
              appendRange(currentValue, range),
            );
            setHoverContextError(
              error instanceof Error
                ? error.message
                : "Unable to load hover context for the visible timeline window.",
            );
          });
        }
      })();
    }
  }, [
    failedDayContextRanges,
    loadedDayContextRanges,
    loadingDayContextRanges,
    shellState,
    visibleRanges,
  ]);

  const activeDayContext =
    state.hoveredDate !== null ? dayContextsByDate[state.hoveredDate] ?? null : null;
  const hoverContextStatus = resolveHoverContextStatus(
    state.hoveredDate,
    dayContextsByDate,
    loadingDayContextRanges,
    failedDayContextRanges,
  );

  if (shellState === "loading") {
    return (
      <main className="flex h-screen items-center justify-center p-5 lg:p-7">
        <div className="mx-auto flex w-full max-w-[56rem] flex-col gap-6">
          <section className="panel-surface min-h-[18rem] p-6">
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">
              Loading exploration
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600">
              Timeline projections and filter catalogs are loading from the API.
            </p>
          </section>
        </div>
      </main>
    );
  }

  if (shellState === "error") {
    return (
      <main className="flex h-screen items-center justify-center p-5 lg:p-7">
        <div className="mx-auto flex w-full max-w-[56rem] flex-col gap-6">
          <section className="panel-surface min-h-[18rem] p-6">
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">
              The exploration shell could not load
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-rose-700">
              {shellError ?? "Timeline bootstrap request failed."}
            </p>
          </section>
        </div>
      </main>
    );
  }

  if (gridState === "loading" && heatmapDays.length === 0) {
    return (
      <main className="flex h-screen items-center justify-center p-5 lg:p-7">
        <div className="mx-auto flex w-full max-w-[56rem] flex-col gap-6">
          <section className="panel-surface min-h-[18rem] p-6">
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">
              Loading filtered exploration
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600">
              Bootstrap metadata is ready. The grid projection is loading for the
              current persistent filters.
            </p>
          </section>
        </div>
      </main>
    );
  }

  return (
    <AppShell
      heatmapDays={heatmapDays}
      viewModes={viewModes}
      persons={persons}
      tags={tags}
      gridState={gridState}
      gridError={gridState === "error" ? gridError : null}
      dayContextsByDate={dayContextsByDate}
      activeDayContext={activeDayContext}
      hoverContextStatus={hoverContextStatus}
      hoverContextError={hoverContextStatus === "error" ? hoverContextError : null}
      onVisibleRangesChange={setVisibleRanges}
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
