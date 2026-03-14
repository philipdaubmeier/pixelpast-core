import type {
  PersonProjection,
  TagProjection,
} from "../../../projections/timeline";

type FilterBarProps = {
  activeViewModeLabel: string;
  selectedPersons: PersonProjection[];
  selectedTags: TagProjection[];
  matchingDayCount: number;
  hasPersistentFilters: boolean;
  gridState: "loading" | "ready" | "error";
  gridError: string | null;
  hoveredDate: string | null;
  onRemovePerson: (personId: string) => void;
  onRemoveTag: (tagPath: string) => void;
  onClear: () => void;
};

export function FilterBar({
  activeViewModeLabel,
  selectedPersons,
  selectedTags,
  matchingDayCount,
  hasPersistentFilters,
  gridState,
  gridError,
  hoveredDate,
  onRemovePerson,
  onRemoveTag,
  onClear,
}: FilterBarProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        View: {activeViewModeLabel}
      </div>
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        {hasPersistentFilters
          ? `${matchingDayCount} matching day${matchingDayCount === 1 ? "" : "s"}`
          : "No persistent filters active"}
      </div>
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        {gridState === "loading"
          ? "Grid: updating"
          : gridState === "error"
            ? gridError ?? "Grid: request failed"
            : "Grid: synced"}
      </div>
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        Hover: {hoveredDate ?? "none"}
      </div>
      {selectedPersons.map((person) => (
        <button
          key={person.id}
          type="button"
          onClick={() => onRemovePerson(person.id)}
          className="rounded-full border border-[color:var(--pp-border)] bg-white px-3 py-1.5 text-[12px] text-slate-700 transition hover:border-slate-900 hover:text-slate-900"
        >
          Person: {person.name} x
        </button>
      ))}
      {selectedTags.map((tag) => (
        <button
          key={tag.path}
          type="button"
          onClick={() => onRemoveTag(tag.path)}
          className="rounded-full border border-[color:var(--pp-border)] bg-white px-3 py-1.5 text-[12px] text-slate-700 transition hover:border-slate-900 hover:text-slate-900"
        >
          Tag: {tag.label} x
        </button>
      ))}
      <button
        type="button"
        onClick={onClear}
        disabled={!hasPersistentFilters}
        className="rounded-full border border-[color:var(--pp-border)] px-3 py-1.5 text-[12px] text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-45"
      >
        Clear selections
      </button>
    </div>
  );
}
