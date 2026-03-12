import { LeftGridPane } from "./layout/LeftGridPane";
import { MainSplitLayout } from "./layout/MainSplitLayout";
import { RightContextPane } from "./layout/RightContextPane";
import { TopBar } from "./layout/TopBar";
import { MapPanel } from "../features/context/components/MapPanel";
import { PersonsPanel } from "../features/context/components/PersonsPanel";
import { TagsPanel } from "../features/context/components/TagsPanel";
import { mockPersons, mockTags } from "../mocks/timeline";
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

  const visiblePersons =
    activeDayContext !== null &&
    activeDayContext.persons.length > 0 &&
    state.hoveredDate !== null
      ? activeDayContext.persons
      : mockPersons;

  const visibleTags =
    activeDayContext !== null &&
    activeDayContext.tags.length > 0 &&
    state.hoveredDate !== null
      ? activeDayContext.tags
      : mockTags;

  return (
    <main className="min-h-screen p-5 lg:p-7">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
        <TopBar
          viewModes={viewModes}
          activeViewMode={state.viewMode}
          selectedPersons={state.selectedPersons}
          selectedTags={state.selectedTags}
          hoveredDate={state.hoveredDate}
          onSelectViewMode={setViewMode}
          onClearSelections={clearSelections}
        />
        <MainSplitLayout
          left={
            <LeftGridPane
              days={heatmapDays}
              viewMode={state.viewMode}
              hoveredDate={state.hoveredDate}
              onHover={setHoveredDate}
            />
          }
          right={
            <RightContextPane>
              <PersonsPanel
                persons={visiblePersons}
                selectedPersonIds={state.selectedPersons}
                hoveredDate={state.hoveredDate}
                onTogglePerson={togglePerson}
              />
              <TagsPanel
                tags={visibleTags}
                selectedTags={state.selectedTags}
                hoveredDate={state.hoveredDate}
                onToggleTag={toggleTag}
              />
              <MapPanel
                hoveredDate={state.hoveredDate}
                mapPoints={activeDayContext?.mapPoints ?? []}
                summary={activeDayContext?.summaryCounts ?? null}
              />
            </RightContextPane>
          }
        />
      </div>
    </main>
  );
}
