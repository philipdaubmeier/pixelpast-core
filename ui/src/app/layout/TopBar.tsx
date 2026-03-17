import logoUrl from "../../assets/pixelpast-logo.svg";
import { FilterBar } from "../../features/timeline/components/FilterBar";
import { GridViewSelector } from "../../features/timeline/components/GridViewSelector";
import type {
  GridViewOption,
  PersonProjection,
  TagProjection,
} from "../../projections/timeline";
import type { GridView, MainView } from "../../state/ui-state";
import { MainViewNavigation } from "./MainViewNavigation";

type TopBarProps = {
  mainView: MainView;
  gridViews: GridViewOption[];
  activeGridView: GridView;
  activeGridViewLabel: string;
  selectedPersons: PersonProjection[];
  selectedTags: TagProjection[];
  matchingDayCount: number;
  hasPersistentFilters: boolean;
  gridState: "loading" | "ready" | "error";
  gridError: string | null;
  hoveredDate: string | null;
  onSelectMainView: (mainView: MainView) => void;
  onSelectGridView: (gridView: GridView) => void;
  onTogglePerson: (personId: string) => void;
  onToggleTag: (tagPath: string) => void;
  onClearSelections: () => void;
};

export function TopBar({
  mainView,
  gridViews,
  activeGridView,
  activeGridViewLabel,
  selectedPersons,
  selectedTags,
  matchingDayCount,
  hasPersistentFilters,
  gridState,
  gridError,
  hoveredDate,
  onSelectMainView,
  onSelectGridView,
  onTogglePerson,
  onToggleTag,
  onClearSelections,
}: TopBarProps) {
  return (
    <header className="thin-scrollbar fixed inset-x-0 top-0 z-20 overflow-x-auto border-b border-[color:var(--pp-border)] bg-[color:rgba(255,249,241,0.96)] shadow-[0_10px_30px_rgba(61,44,15,0.06)] backdrop-blur-sm">
      <div className="min-w-max px-4 py-2 lg:px-5">
        <div className="flex min-h-[4rem] items-center gap-4">
          <img
            src={logoUrl}
            alt="PixelPast"
            className="h-12 w-auto shrink-0 lg:h-[3.35rem]"
          />
          <div className="flex min-w-max items-center gap-3 lg:gap-4">
            <MainViewNavigation
              activeMainView={mainView}
              onSelect={onSelectMainView}
            />
            <FilterBar
              activeGridViewLabel={activeGridViewLabel}
              selectedPersons={selectedPersons}
              selectedTags={selectedTags}
              matchingDayCount={matchingDayCount}
              hasPersistentFilters={hasPersistentFilters}
              gridState={gridState}
              gridError={gridError}
              hoveredDate={hoveredDate}
              onRemovePerson={onTogglePerson}
              onRemoveTag={onToggleTag}
              onClear={onClearSelections}
            />
          </div>
        </div>
        <div className="flex min-h-[2.5rem] items-center pl-[4.4rem] lg:pl-[5rem]">
          <div className="flex items-center gap-3 rounded-full bg-[color:rgba(255,255,255,0.45)] px-3 py-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Day Grid
            </span>
            <GridViewSelector
              options={gridViews}
              activeGridView={activeGridView}
              onSelect={onSelectGridView}
            />
          </div>
        </div>
      </div>
    </header>
  );
}
