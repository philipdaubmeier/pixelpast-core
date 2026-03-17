import type { GridViewOption } from "../../../projections/timeline";
import type { GridView } from "../../../state/ui-state";

type GridViewSelectorProps = {
  options: GridViewOption[];
  activeGridView: GridView;
  onSelect: (gridView: GridView) => void;
};

export function GridViewSelector({
  options,
  activeGridView,
  onSelect,
}: GridViewSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onSelect(option.id)}
          className={[
            "rounded-full border px-3 py-1.5 text-[11px] font-medium transition",
            option.id === activeGridView
              ? "border-slate-700 bg-slate-200/85 text-slate-900"
              : "border-[color:var(--pp-border)] bg-white/60 text-slate-600 hover:bg-white/80",
          ].join(" ")}
          title={option.description}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
