import { useMemo, useState, type ReactNode } from "react";
import { HoverSummaryPanel } from "../features/context/components/HoverSummaryPanel";
import { LeftGridPane } from "./layout/LeftGridPane";
import { MainSplitLayout } from "./layout/MainSplitLayout";
import { RightContextPane } from "./layout/RightContextPane";
import { TopBar } from "./layout/TopBar";
import { MapPanel } from "../features/context/components/MapPanel";
import { PersonsPanel } from "../features/context/components/PersonsPanel";
import { TagsPanel } from "../features/context/components/TagsPanel";
import { ManageDataOverlay } from "../features/manage-data/components/ManageDataOverlay";
import { PhotoAlbumView } from "../features/photo-album/components/PhotoAlbumView";
import {
  defaultAlbumChromeState,
  type AlbumNodeSelection,
} from "../features/photo-album/types";
import { SocialGraphView } from "../features/social-graph/components/SocialGraphView";
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
import type { SocialGraphProjection } from "../projections/socialGraph";
import { getGridViewColorToken } from "../projections/timeline";
import { useUiState } from "../state/UiStateContext";
import type { PersonGroupProjection } from "../api/personGroups";

type HoverContextStatus = "idle" | "loading" | "ready" | "error";
type LoadState = "loading" | "ready" | "error";

type AppShellProps = {
  heatmapDays: HeatmapDayProjection[];
  gridViews: GridViewOption[];
  persons: PersonProjection[];
  personGroups: PersonGroupProjection[];
  personGroupCatalogState: LoadState;
  personGroupCatalogError: string | null;
  tags: TagProjection[];
  timelineState: LoadState;
  timelineError: string | null;
  dayContextsByDate: Record<string, DayContextProjection>;
  activeDayContext: DayContextProjection | null;
  hoverContextStatus: HoverContextStatus;
  hoverContextError: string | null;
  onVisibleRangesChange: (ranges: DateRange[]) => void;
  onRefreshPersonGroups: () => void;
  socialGraphState: LoadState;
  socialGraphError: string | null;
  socialGraph: SocialGraphProjection | null;
  socialGraphMaxPeoplePerAsset: number;
  onChangeSocialGraphMaxPeoplePerAsset: (value: number) => void;
};

function TimelineMainContent({
  heatmapDays,
  persons,
  tags,
  gridViews,
  dayContextsByDate,
  activeDayContext,
  hoverContextStatus,
  hoverContextError,
  onVisibleRangesChange,
}: {
  heatmapDays: HeatmapDayProjection[];
  persons: PersonProjection[];
  tags: TagProjection[];
  gridViews: GridViewOption[];
  dayContextsByDate: Record<string, DayContextProjection>;
  activeDayContext: DayContextProjection | null;
  hoverContextStatus: HoverContextStatus;
  hoverContextError: string | null;
  onVisibleRangesChange: (ranges: DateRange[]) => void;
}) {
  const { state, setHoveredDate, togglePerson, toggleTag } = useUiState();
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
  const activeGridColorToken = getGridViewColorToken(gridViews, state.gridView);
  const hasPersistentFilters =
    state.selectedPersons.length > 0 ||
    state.selectedPersonGroupIds.length > 0 ||
    state.selectedTags.length > 0;

  return (
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
            contextLabel={state.hoveredDate}
            contextStatus={hoverContextStatus}
            contextError={hoverContextError}
            onTogglePerson={togglePerson}
          />
          <TagsPanel
            tags={visibleTags}
            contextLabel={state.hoveredDate}
            contextStatus={hoverContextStatus}
            contextError={hoverContextError}
            onToggleTag={toggleTag}
          />
          <MapPanel
            contextLabel={state.hoveredDate}
            mapPoints={mapProjection.mapPoints}
            hasPersistentFilters={hasPersistentFilters}
            contextStatus={hoverContextStatus}
            contextError={hoverContextError}
          />
          <HoverSummaryPanel summary={mapProjection.mapSummary} />
        </RightContextPane>
      }
    />
  );
}

function MainContentFrame({
  mainView,
  children,
}: {
  mainView: "day_grid" | "photo_album" | "social_graph";
  children: ReactNode;
}) {
  return (
    <div
      className={[
        "h-full px-2 pb-2 lg:px-2.5 lg:pb-2.5",
        mainView === "day_grid" ? "pt-[7.3rem] lg:pt-[7.2rem]" : "pt-[4.9rem]",
      ].join(" ")}
    >
      {children}
    </div>
  );
}

export function AppShell({
  heatmapDays,
  gridViews,
  persons,
  personGroups,
  personGroupCatalogState,
  personGroupCatalogError,
  tags,
  timelineState,
  timelineError,
  dayContextsByDate,
  activeDayContext,
  hoverContextStatus,
  hoverContextError,
  onVisibleRangesChange,
  onRefreshPersonGroups,
  socialGraphState,
  socialGraphError,
  socialGraph,
  socialGraphMaxPeoplePerAsset,
  onChangeSocialGraphMaxPeoplePerAsset,
}: AppShellProps) {
  const [isManageDataOpen, setManageDataOpen] = useState(false);
  const [albumSelection, setAlbumSelection] = useState<AlbumNodeSelection | null>(
    null,
  );
  const [albumSelectedAssetId, setAlbumSelectedAssetId] = useState<number | null>(
    null,
  );
  const [expandedFolderIds, setExpandedFolderIds] = useState<number[]>([]);
  const [expandedCollectionIds, setExpandedCollectionIds] = useState<number[]>([]);
  const [albumChromeState, setAlbumChromeState] = useState(defaultAlbumChromeState);
  const {
    state,
    clearSelections,
    setGridView,
    setMainView,
    togglePerson,
    togglePersonGroup,
    toggleTag,
  } = useUiState();

  const selectedPersons = useMemo(
    () => resolveSelectedPersons(state.selectedPersons, persons),
    [persons, state.selectedPersons],
  );
  const selectedTags = useMemo(
    () => resolveSelectedTags(state.selectedTags, tags),
    [state.selectedTags, tags],
  );
  const selectedPersonGroups = useMemo(() => {
    const groupsById = new Map(personGroups.map((group) => [group.id, group]));

    return state.selectedPersonGroupIds.map((groupId) => {
      const group = groupsById.get(groupId);

      return (
        group ?? {
          id: groupId,
          name: `Group ${groupId}`,
          memberCount: 0,
          colorIndex: null,
        }
      );
    });
  }, [personGroups, state.selectedPersonGroupIds]);
  const hasPersistentFilters =
    state.selectedPersons.length > 0 ||
    state.selectedPersonGroupIds.length > 0 ||
    state.selectedTags.length > 0;
  const activeGridView =
    gridViews.find((gridView) => gridView.id === state.gridView) ?? null;
  const matchingDayCount = useMemo(
    () =>
      heatmapDays.filter((day) => day.color !== "empty").length,
    [heatmapDays],
  );

  return (
    <main className="h-screen overflow-hidden">
      <TopBar
        mainView={state.mainView}
        gridViews={gridViews}
        activeGridView={state.gridView}
        activeGridViewLabel={activeGridView?.label ?? state.gridView}
        selectedPersons={selectedPersons}
        selectedPersonGroups={selectedPersonGroups}
        selectedTags={selectedTags}
        personGroups={personGroups}
        personGroupCatalogState={personGroupCatalogState}
        personGroupCatalogError={personGroupCatalogError}
        resultSummary={
          state.mainView === "day_grid"
            ? `${matchingDayCount} matching day${matchingDayCount === 1 ? "" : "s"}`
            : state.mainView === "photo_album"
              ? albumChromeState.resultSummary
              : `${socialGraph?.persons.length ?? 0} person node${
                  (socialGraph?.persons.length ?? 0) === 1 ? "" : "s"
                } in view`
        }
        hasPersistentFilters={hasPersistentFilters}
        transportState={
          state.mainView === "day_grid"
            ? timelineState
            : state.mainView === "photo_album"
              ? albumChromeState.transportState
              : socialGraphState
        }
        transportError={
          state.mainView === "day_grid"
            ? timelineError
            : state.mainView === "photo_album"
              ? albumChromeState.transportError
              : socialGraphError
        }
        hoverLabel={
          state.mainView === "day_grid"
            ? state.hoveredDate ?? "none"
            : state.mainView === "photo_album"
              ? albumChromeState.hoverLabel
              : "not active"
        }
        onSelectMainView={setMainView}
        onSelectGridView={setGridView}
        onTogglePerson={togglePerson}
        onTogglePersonGroup={togglePersonGroup}
        onToggleTag={toggleTag}
        onClearSelections={clearSelections}
        isManageDataOpen={isManageDataOpen}
        onToggleManageData={() =>
          setManageDataOpen((currentValue) => {
            const nextValue = !currentValue;
            if (!nextValue) {
              onRefreshPersonGroups();
            }
            return nextValue;
          })
        }
      />
      {state.mainView === "day_grid" ? (
        <MainContentFrame mainView="day_grid">
          <TimelineMainContent
            heatmapDays={heatmapDays}
            persons={persons}
            tags={tags}
            gridViews={gridViews}
            dayContextsByDate={dayContextsByDate}
            activeDayContext={activeDayContext}
            hoverContextStatus={hoverContextStatus}
            hoverContextError={hoverContextError}
            onVisibleRangesChange={onVisibleRangesChange}
          />
        </MainContentFrame>
      ) : state.mainView === "photo_album" ? (
        <MainContentFrame mainView="photo_album">
          <PhotoAlbumView
            selectedPersons={selectedPersons}
            selectedTags={selectedTags}
            selectedPersonIds={state.selectedPersons}
            selectedPersonGroupIds={state.selectedPersonGroupIds}
            selectedTagPaths={state.selectedTags}
            hasPersistentFilters={hasPersistentFilters}
            selection={albumSelection}
            selectedAssetId={albumSelectedAssetId}
            expandedFolderIds={expandedFolderIds}
            expandedCollectionIds={expandedCollectionIds}
            onSelectionChange={setAlbumSelection}
            onSelectedAssetChange={setAlbumSelectedAssetId}
            onExpandedFolderIdsChange={setExpandedFolderIds}
            onExpandedCollectionIdsChange={setExpandedCollectionIds}
            onTogglePerson={togglePerson}
            onTogglePersonGroup={togglePersonGroup}
            onToggleTag={toggleTag}
            onChromeStateChange={(nextState) =>
              setAlbumChromeState((currentState) =>
                currentState.transportState === nextState.transportState &&
                currentState.transportError === nextState.transportError &&
                currentState.resultSummary === nextState.resultSummary &&
                currentState.hoverLabel === nextState.hoverLabel
                  ? currentState
                  : nextState,
              )
            }
          />
        </MainContentFrame>
      ) : (
        <MainContentFrame mainView="social_graph">
          <SocialGraphView
            state={socialGraphState}
            error={socialGraphError}
            graph={socialGraph}
            maxPeoplePerAsset={socialGraphMaxPeoplePerAsset}
            selectedPersons={selectedPersons}
            selectedPersonGroups={selectedPersonGroups}
            selectedTags={selectedTags}
            onChangeMaxPeoplePerAsset={onChangeSocialGraphMaxPeoplePerAsset}
            onTogglePerson={togglePerson}
          />
        </MainContentFrame>
      )}
      <ManageDataOverlay
        isOpen={isManageDataOpen}
        onClose={() => {
          setManageDataOpen(false);
          onRefreshPersonGroups();
        }}
      />
    </main>
  );
}
