import { LeftGridPane } from "./layout/LeftGridPane";
import { MainSplitLayout } from "./layout/MainSplitLayout";
import { RightContextPane } from "./layout/RightContextPane";
import { TopBar } from "./layout/TopBar";
import { MapPanel } from "../features/context/components/MapPanel";
import { PersonsPanel } from "../features/context/components/PersonsPanel";
import { TagsPanel } from "../features/context/components/TagsPanel";
import { mockDayContexts, mockPersons, mockTags } from "../mocks/timeline";
import { buildExplorationProjection } from "../projections/exploration";
import type {
  DayContextProjection,
  HeatmapDayProjection,
  ViewModeOption,
} from "../projections/timeline";
import { useUiState } from "../state/UiStateContext";

type AppShellProps = {
  heatmapDays: HeatmapDayProjection[];
  viewModes: ViewModeOption[];
  activeDayContext: DayContextProjection | null;
};

export function AppShell({
  heatmapDays,
  viewModes,
  activeDayContext,
}: AppShellProps) {
  const {
    state,
    clearSelections,
    setHoveredDate,
    setViewMode,
    togglePerson,
    toggleTag,
  } = useUiState();

  const exploration = buildExplorationProjection({
    heatmapDays,
    dayContextsByDate: mockDayContexts,
    activeDayContext,
    allPersons: mockPersons,
    allTags: mockTags,
    state,
  });
  const activeViewMode =
    viewModes.find((viewMode) => viewMode.id === state.viewMode) ?? null;

  return (
    <main className="min-h-screen p-5 lg:p-7">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
        <TopBar
          viewModes={viewModes}
          activeViewMode={state.viewMode}
          activeViewModeLabel={activeViewMode?.label ?? state.viewMode}
          selectedPersons={exploration.selectedPersons}
          selectedTags={exploration.selectedTags}
          matchingDayCount={exploration.matchingDayCount}
          hasPersistentFilters={exploration.hasPersistentFilters}
          hoveredDate={state.hoveredDate}
          onSelectViewMode={setViewMode}
          onTogglePerson={togglePerson}
          onToggleTag={toggleTag}
          onClearSelections={clearSelections}
        />
        <MainSplitLayout
          left={
            <LeftGridPane
              days={exploration.gridDays}
              viewMode={state.viewMode}
              hoveredDate={state.hoveredDate}
              onHover={setHoveredDate}
            />
          }
          right={
            <RightContextPane>
              <PersonsPanel
                persons={exploration.visiblePersons}
                hoveredDate={state.hoveredDate}
                onTogglePerson={togglePerson}
              />
              <TagsPanel
                tags={exploration.visibleTags}
                hoveredDate={state.hoveredDate}
                onToggleTag={toggleTag}
              />
              <MapPanel
                hoveredDate={state.hoveredDate}
                mapPoints={exploration.mapPoints}
                summary={exploration.mapSummary}
                hasPersistentFilters={exploration.hasPersistentFilters}
              />
            </RightContextPane>
          }
        />
      </div>
    </main>
  );
}
