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
  const { state } = useUiState();
  const isMountedRef = useRef(true);
  const [shellState, setShellState] = useState<ShellLoadState>("loading");
  const [shellError, setShellError] = useState<string | null>(null);
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
        const exploration = await timelineApi.getExploration();

        if (!isMountedRef.current) {
          return;
        }

        startTransition(() => {
          setHeatmapDays(exploration.heatmapDays);
          setViewModes(exploration.viewModes);
          setPersons(exploration.persons);
          setTags(exploration.tags);
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
      <main className="min-h-screen p-5 lg:p-7">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
          <section className="panel-surface min-h-[18rem] p-6">
            <p className="panel-title">Loading</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">
              Connecting the exploration shell to the Python API
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
      <main className="min-h-screen p-5 lg:p-7">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
          <section className="panel-surface min-h-[18rem] p-6">
            <p className="panel-title">Unavailable</p>
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

  return (
    <AppShell
      heatmapDays={heatmapDays}
      viewModes={viewModes}
      persons={persons}
      tags={tags}
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
