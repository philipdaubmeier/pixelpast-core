import { FilterBar } from "../../features/timeline/components/FilterBar";
import { ViewModeSelector } from "../../features/timeline/components/ViewModeSelector";
import type { ViewModeOption } from "../../projections/timeline";
import type { ViewMode } from "../../state/ui-state";

type TopBarProps = {
  viewModes: ViewModeOption[];
  activeViewMode: ViewMode;
  selectedPersons: string[];
  selectedTags: string[];
  hoveredDate: string | null;
  onSelectViewMode: (viewMode: ViewMode) => void;
  onClearSelections: () => void;
};

export function TopBar({
  viewModes,
  activeViewMode,
  selectedPersons,
  selectedTags,
  hoveredDate,
  onSelectViewMode,
  onClearSelections,
}: TopBarProps) {
  return (
    <header className="panel-surface-strong flex flex-col gap-5 p-5 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-xl space-y-3">
        <div>
          <p className="panel-title">PixelPast</p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
            Time stays visible.
          </h1>
        </div>
        <p className="panel-copy">
          Desktop-first shell for the chronology grid, persistent exploration
          controls, and context panes that react without replacing the timeline.
        </p>
      </div>
      <div className="flex max-w-3xl flex-1 flex-col gap-4">
        <ViewModeSelector
          options={viewModes}
          activeViewMode={activeViewMode}
          onSelect={onSelectViewMode}
        />
        <FilterBar
          selectedPersons={selectedPersons}
          selectedTags={selectedTags}
          hoveredDate={hoveredDate}
          onClear={onClearSelections}
        />
        <input
          type="text"
          placeholder="Search and richer controls land here in later UI tasks"
          disabled
          className="rounded-full border border-[color:var(--pp-border)] bg-white/55 px-4 py-3 text-sm text-slate-500"
        />
      </div>
    </header>
  );
}
