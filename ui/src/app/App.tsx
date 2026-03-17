import { startTransition, useEffect, useRef, useState } from "react";
import { socialGraphApi } from "../api/socialGraph";
import { timelineApi } from "../api/timeline";
import type { SocialGraphProjection } from "../projections/socialGraph";
import type {
  DateRange,
  DayContextProjection,
  GridViewOption,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
} from "../projections/timeline";
import { UiStateProvider, useUiState } from "../state/UiStateContext";
import { AppShell } from "./AppShell";

type ShellLoadState = "loading" | "ready" | "error";
type ViewLoadState = "loading" | "ready" | "error";
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
  const { state, setGridView, setHoveredDate } = useUiState();
  const isMountedRef = useRef(true);
  const latestTimelineRequestIdRef = useRef(0);
  const latestSocialGraphRequestIdRef = useRef(0);
  const latestDayContextScopeRef = useRef("");
  const [shellState, setShellState] = useState<ShellLoadState>("loading");
  const [shellError, setShellError] = useState<string | null>(null);
  const [timelineState, setTimelineState] = useState<ViewLoadState>("loading");
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [socialGraphState, setSocialGraphState] = useState<ViewLoadState>("loading");
  const [socialGraphError, setSocialGraphError] = useState<string | null>(null);
  const [explorationRange, setExplorationRange] = useState<DateRange | null>(null);
  const [heatmapDays, setHeatmapDays] = useState<HeatmapDayProjection[]>([]);
  const [gridViews, setGridViews] = useState<GridViewOption[]>([]);
  const [persons, setPersons] = useState<PersonProjection[]>([]);
  const [tags, setTags] = useState<TagProjection[]>([]);
  const [socialGraph, setSocialGraph] = useState<SocialGraphProjection | null>(
    null,
  );
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
  const dayContextScope = JSON.stringify({
    gridView: state.gridView,
    selectedPersons: [...state.selectedPersons].sort(),
    selectedTags: [...state.selectedTags].sort(),
  });

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
          setGridViews(bootstrap.gridViews);
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
    if (shellState !== "ready" || gridViews.length === 0) {
      return;
    }

    if (gridViews.some((gridView) => gridView.id === state.gridView)) {
      return;
    }

    setGridView(gridViews[0].id);
  }, [gridViews, setGridView, shellState, state.gridView]);

  useEffect(() => {
    if (
      state.mainView !== "day_grid" ||
      shellState !== "ready" ||
      explorationRange === null ||
      gridViews.length === 0 ||
      !gridViews.some((gridView) => gridView.id === state.gridView)
    ) {
      return;
    }

    const requestId = latestTimelineRequestIdRef.current + 1;
    latestTimelineRequestIdRef.current = requestId;
    setHoveredDate(null);

    startTransition(() => {
      setTimelineState("loading");
      setTimelineError(null);
    });

    void (async () => {
      try {
        const grid = await timelineApi.getExplorationGrid(explorationRange, {
          gridView: state.gridView,
          selectedPersons: state.selectedPersons,
          selectedTags: state.selectedTags,
        });

        if (
          !isMountedRef.current ||
          latestTimelineRequestIdRef.current !== requestId
        ) {
          return;
        }

        startTransition(() => {
          setHeatmapDays(grid.heatmapDays);
          setTimelineState("ready");
          setTimelineError(null);
        });
      } catch (error) {
        if (
          !isMountedRef.current ||
          latestTimelineRequestIdRef.current !== requestId
        ) {
          return;
        }

        startTransition(() => {
          setTimelineState("error");
          setTimelineError(
            error instanceof Error
              ? error.message
              : "Unable to load the filtered exploration grid.",
          );
        });
      }
    })();
  }, [
    explorationRange,
    gridViews,
    setHoveredDate,
    shellState,
    state.gridView,
    state.mainView,
    state.selectedPersons,
    state.selectedTags,
  ]);

  useEffect(() => {
    if (
      state.mainView !== "social_graph" ||
      shellState !== "ready" ||
      explorationRange === null
    ) {
      return;
    }

    const requestId = latestSocialGraphRequestIdRef.current + 1;
    latestSocialGraphRequestIdRef.current = requestId;

    startTransition(() => {
      setSocialGraphState("loading");
      setSocialGraphError(null);
    });

    void (async () => {
      try {
        const graph = await socialGraphApi.getSocialGraph(explorationRange, {
          selectedPersons: state.selectedPersons,
        });

        if (
          !isMountedRef.current ||
          latestSocialGraphRequestIdRef.current !== requestId
        ) {
          return;
        }

        startTransition(() => {
          setSocialGraph(graph);
          setSocialGraphState("ready");
          setSocialGraphError(null);
        });
      } catch (error) {
        if (
          !isMountedRef.current ||
          latestSocialGraphRequestIdRef.current !== requestId
        ) {
          return;
        }

        startTransition(() => {
          setSocialGraphState("error");
          setSocialGraphError(
            error instanceof Error
              ? error.message
              : "Unable to load the social graph.",
          );
        });
      }
    })();
  }, [explorationRange, shellState, state.mainView, state.selectedPersons]);

  useEffect(() => {
    if (state.mainView !== "day_grid") {
      return;
    }

    latestDayContextScopeRef.current = dayContextScope;
    startTransition(() => {
      setDayContextsByDate({});
      setLoadedDayContextRanges([]);
      setLoadingDayContextRanges([]);
      setFailedDayContextRanges([]);
      setHoverContextError(null);
    });
  }, [dayContextScope, state.mainView]);

  useEffect(() => {
    if (
      state.mainView !== "day_grid" ||
      shellState !== "ready" ||
      visibleRanges.length === 0
    ) {
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
      const requestScope = dayContextScope;
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
          const response = await timelineApi.getDayContextRange(range, {
            gridView: state.gridView,
            selectedPersons: state.selectedPersons,
            selectedTags: state.selectedTags,
          });

          if (
            !isMountedRef.current ||
            latestDayContextScopeRef.current !== requestScope
          ) {
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
          if (
            !isMountedRef.current ||
            latestDayContextScopeRef.current !== requestScope
          ) {
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
    dayContextScope,
    failedDayContextRanges,
    loadedDayContextRanges,
    loadingDayContextRanges,
    shellState,
    state.gridView,
    state.mainView,
    state.selectedPersons,
    state.selectedTags,
    visibleRanges,
  ]);

  const activeDayContext =
    state.mainView === "day_grid" && state.hoveredDate !== null
      ? dayContextsByDate[state.hoveredDate] ?? null
      : null;
  const hoverContextStatus =
    state.mainView === "day_grid"
      ? resolveHoverContextStatus(
          state.hoveredDate,
          dayContextsByDate,
          loadingDayContextRanges,
          failedDayContextRanges,
        )
      : "idle";

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

  return (
    <AppShell
      heatmapDays={heatmapDays}
      gridViews={gridViews}
      persons={persons}
      tags={tags}
      timelineState={timelineState}
      timelineError={timelineState === "error" ? timelineError : null}
      dayContextsByDate={dayContextsByDate}
      activeDayContext={activeDayContext}
      hoverContextStatus={hoverContextStatus}
      hoverContextError={hoverContextStatus === "error" ? hoverContextError : null}
      onVisibleRangesChange={setVisibleRanges}
      socialGraphState={socialGraphState}
      socialGraphError={socialGraphState === "error" ? socialGraphError : null}
      socialGraph={socialGraph}
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
