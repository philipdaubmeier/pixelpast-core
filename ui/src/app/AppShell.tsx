import { useMemo } from "react";
import { LeftGridPane } from "./layout/LeftGridPane";
import { MainSplitLayout } from "./layout/MainSplitLayout";
import { RightContextPane } from "./layout/RightContextPane";
import { TopBar } from "./layout/TopBar";
import { MapPanel } from "../features/context/components/MapPanel";
import { PersonsPanel } from "../features/context/components/PersonsPanel";
import { TagsPanel } from "../features/context/components/TagsPanel";
import {
  buildGridDays,
  buildMapProjection,
  buildVisiblePersons,
  buildVisibleTags,
  resolveSelectedPersons,
  resolveSelectedTags,
} from "../projections/exploration";
import type {
  DateRange,
  DayContextProjection,
  GridViewOption,
  HeatmapDayProjection,
  PersonProjection,
  TagProjection,
} from "../projections/timeline";
import { getGridViewColorToken } from "../projections/timeline";
import { useUiState } from "../state/UiStateContext";

type HoverContextStatus = "idle" | "loading" | "ready" | "error";
type GridLoadState = "loading" | "ready" | "error";

type AppShellProps = {
  heatmapDays: HeatmapDayProjection[];
  gridViews: GridViewOption[];
  persons: PersonProjection[];
  tags: TagProjection[];
  gridState: GridLoadState;
  gridError: string | null;
  dayContextsByDate: Record<string, DayContextProjection>;
  activeDayContext: DayContextProjection | null;
  hoverContextStatus: HoverContextStatus;
  hoverContextError: string | null;
  onVisibleRangesChange: (ranges: DateRange[]) => void;
};

export function AppShell({
  heatmapDays,
  gridViews,
  persons,
  tags,
  gridState,
  gridError,
  dayContextsByDate,
  activeDayContext,
  hoverContextStatus,
  hoverContextError,
  onVisibleRangesChange,
}: AppShellProps) {
  const {
    state,
    clearSelections,
    setHoveredDate,
    setGridView,
    setMainView,
    togglePerson,
    toggleTag,
  } = useUiState();

  const gridDays = useMemo(
    () => buildGridDays(heatmapDays, state.selectedPersons, state.selectedTags),
    [heatmapDays, state.selectedPersons, state.selectedTags],
  );
  const selectedPersons = useMemo(
    () => resolveSelectedPersons(state.selectedPersons, persons),
    [persons, state.selectedPersons],
  );
  const selectedTags = useMemo(
    () => resolveSelectedTags(state.selectedTags, tags),
    [state.selectedTags, tags],
  );
  const hoveredPersons =
    state.hoveredDate !== null ? activeDayContext?.persons ?? [] : [];
  const hoveredTags =
    state.hoveredDate !== null ? activeDayContext?.tags ?? [] : [];
  const visiblePersons = useMemo(
    () => buildVisiblePersons(selectedPersons, hoveredPersons, persons),
    [hoveredPersons, persons, selectedPersons],
  );
  const visibleTags = useMemo(
    () => buildVisibleTags(selectedTags, hoveredTags, tags),
    [hoveredTags, selectedTags, tags],
  );
  const matchingDayCount = useMemo(
    () => gridDays.filter((day) => day.color !== "empty").length,
    [gridDays],
  );
  const mapProjection = useMemo(
    () =>
      buildMapProjection(
        state.hoveredDate,
        activeDayContext,
        gridDays,
        dayContextsByDate,
      ),
    [activeDayContext, dayContextsByDate, gridDays, state.hoveredDate],
  );
  const hasPersistentFilters =
    state.selectedPersons.length > 0 || state.selectedTags.length > 0;
  const activeGridView =
    gridViews.find((gridView) => gridView.id === state.gridView) ?? null;
  const activeGridColorToken = getGridViewColorToken(gridViews, state.gridView);

  return (
    <main className="h-screen overflow-hidden">
      <TopBar
        mainView={state.mainView}
        gridViews={gridViews}
        activeGridView={state.gridView}
        activeGridViewLabel={activeGridView?.label ?? state.gridView}
        selectedPersons={selectedPersons}
        selectedTags={selectedTags}
        matchingDayCount={matchingDayCount}
        hasPersistentFilters={hasPersistentFilters}
        gridState={gridState}
        gridError={gridError}
        hoveredDate={state.hoveredDate}
        onSelectMainView={setMainView}
        onSelectGridView={setGridView}
        onTogglePerson={togglePerson}
        onToggleTag={toggleTag}
        onClearSelections={clearSelections}
      />
      <div className="h-full px-2 pb-2 pt-[7.3rem] lg:px-2.5 lg:pb-2.5 lg:pt-[7.2rem]">
        <MainSplitLayout
          left={
            <LeftGridPane
              days={gridDays}
              viewColorToken={activeGridColorToken}
              onVisibleRangesChange={onVisibleRangesChange}
              onHover={setHoveredDate}
            />
          }
          right={
            <RightContextPane>
              <PersonsPanel
                persons={visiblePersons}
                hoveredDate={state.hoveredDate}
                hoverContextStatus={hoverContextStatus}
                hoverContextError={hoverContextError}
                onTogglePerson={togglePerson}
              />
              <TagsPanel
                tags={visibleTags}
                hoveredDate={state.hoveredDate}
                hoverContextStatus={hoverContextStatus}
                hoverContextError={hoverContextError}
                onToggleTag={toggleTag}
              />
              <MapPanel
                hoveredDate={state.hoveredDate}
                mapPoints={mapProjection.mapPoints}
                summary={mapProjection.mapSummary}
                hasPersistentFilters={hasPersistentFilters}
                hoverContextStatus={hoverContextStatus}
                hoverContextError={hoverContextError}
              />
            </RightContextPane>
          }
        />
      </div>
    </main>
  );
}
