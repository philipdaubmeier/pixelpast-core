import logoUrl from "../../assets/pixelpast-logo.svg";
import { FilterBar } from "../../features/timeline/components/FilterBar";
import { ViewModeSelector } from "../../features/timeline/components/ViewModeSelector";
import type {
  PersonProjection,
  TagProjection,
  ViewModeOption,
} from "../../projections/timeline";
import type { ViewMode } from "../../state/ui-state";

type TopBarProps = {
  viewModes: ViewModeOption[];
  activeViewMode: ViewMode;
  activeViewModeLabel: string;
  selectedPersons: PersonProjection[];
  selectedTags: TagProjection[];
  matchingDayCount: number;
  hasPersistentFilters: boolean;
  hoveredDate: string | null;
  onSelectViewMode: (viewMode: ViewMode) => void;
  onTogglePerson: (personId: string) => void;
  onToggleTag: (tagPath: string) => void;
  onClearSelections: () => void;
};

export function TopBar({
  viewModes,
  activeViewMode,
  activeViewModeLabel,
  selectedPersons,
  selectedTags,
  matchingDayCount,
  hasPersistentFilters,
  hoveredDate,
  onSelectViewMode,
  onTogglePerson,
  onToggleTag,
  onClearSelections,
}: TopBarProps) {
  return (
    <header className="thin-scrollbar fixed inset-x-0 top-0 z-20 overflow-x-auto border-b border-[color:var(--pp-border)] bg-[color:rgba(255,249,241,0.96)] shadow-[0_10px_30px_rgba(61,44,15,0.06)] backdrop-blur-sm">
      <div className="flex min-h-[4rem] min-w-max items-center gap-4 px-4 py-2 lg:px-5">
        <img
          src={logoUrl}
          alt="PixelPast"
          className="h-12 w-auto shrink-0 lg:h-[3.35rem]"
        />
        <div className="flex min-w-max items-center gap-3 lg:gap-4">
          <ViewModeSelector
            options={viewModes}
            activeViewMode={activeViewMode}
            onSelect={onSelectViewMode}
          />
          <FilterBar
            activeViewModeLabel={activeViewModeLabel}
            selectedPersons={selectedPersons}
            selectedTags={selectedTags}
            matchingDayCount={matchingDayCount}
            hasPersistentFilters={hasPersistentFilters}
            hoveredDate={hoveredDate}
            onRemovePerson={onTogglePerson}
            onRemoveTag={onToggleTag}
            onClear={onClearSelections}
          />
        </div>
      </div>
    </header>
  );
}
