import type { HeatmapDayProjection } from "../../../projections/timeline";
import type { ViewMode } from "../../../state/ui-state";
import { DayCell } from "./DayCell";

type YearGridProps = {
  year: number;
  days: HeatmapDayProjection[];
  viewMode: ViewMode;
  hoveredDate: string | null;
  onHover: (date: string | null) => void;
};

export function YearGrid({
  year,
  days,
  viewMode,
  hoveredDate,
  onHover,
}: YearGridProps) {
  return (
    <section className="grid grid-cols-[52px_minmax(0,1fr)] gap-4">
      <div className="flex items-center justify-center">
        <span className="-rotate-90 text-xs font-semibold uppercase tracking-[0.35em] text-slate-500">
          {year}
        </span>
      </div>
      <div className="rounded-[22px] border border-white/70 bg-white/55 p-4">
        <div className="grid auto-cols-max grid-flow-col grid-rows-7 gap-1">
          {days.map((day) => (
            <DayCell
              key={day.date}
              day={day}
              viewMode={viewMode}
              isHovered={hoveredDate === day.date}
              onHover={onHover}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
