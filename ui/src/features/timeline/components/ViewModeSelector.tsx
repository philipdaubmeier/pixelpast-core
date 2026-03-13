import type { ViewModeOption } from "../../../projections/timeline";
import type { ViewMode } from "../../../state/ui-state";

type ViewModeSelectorProps = {
  options: ViewModeOption[];
  activeViewMode: ViewMode;
  onSelect: (viewMode: ViewMode) => void;
};

export function ViewModeSelector({
  options,
  activeViewMode,
  onSelect,
}: ViewModeSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onSelect(option.id)}
          className={[
            "rounded-full px-3 py-1.5 text-[12px] transition",
            option.id === activeViewMode
              ? "bg-slate-900 text-white shadow-[0_10px_28px_rgba(15,23,42,0.16)]"
              : "bg-white/70 text-slate-700 hover:bg-white",
          ].join(" ")}
          title={option.description}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
