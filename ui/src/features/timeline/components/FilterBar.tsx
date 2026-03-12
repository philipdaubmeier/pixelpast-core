type FilterBarProps = {
  selectedPersons: string[];
  selectedTags: string[];
  hoveredDate: string | null;
  onClear: () => void;
};

export function FilterBar({
  selectedPersons,
  selectedTags,
  hoveredDate,
  onClear,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="rounded-full bg-white/70 px-4 py-2 text-sm text-slate-700">
        {selectedPersons.length} person filter
        {selectedPersons.length === 1 ? "" : "s"}
      </div>
      <div className="rounded-full bg-white/70 px-4 py-2 text-sm text-slate-700">
        {selectedTags.length} tag filter{selectedTags.length === 1 ? "" : "s"}
      </div>
      <div className="rounded-full bg-white/70 px-4 py-2 text-sm text-slate-700">
        Hover: {hoveredDate ?? "none"}
      </div>
      <button
        type="button"
        onClick={onClear}
        className="rounded-full border border-[color:var(--pp-border)] px-4 py-2 text-sm text-slate-700 transition hover:bg-white"
      >
        Clear selections
      </button>
    </div>
  );
}
