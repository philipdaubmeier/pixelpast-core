import { forwardRef } from "react";
import type { HeatmapDayRenderProjection } from "../../../projections/exploration";
import type { ViewMode } from "../../../state/ui-state";
import { DayCell } from "./DayCell";

type YearGridProps = {
  year: number;
  days: HeatmapDayRenderProjection[];
  viewMode: ViewMode;
  hoveredDate: string | null;
  onHover: (date: string | null) => void;
};

export const YearGrid = forwardRef<HTMLElement, YearGridProps>(function YearGrid(
  { year, days, viewMode, hoveredDate, onHover },
  ref,
) {
  const orderedDays = [...days].sort((leftDay, rightDay) =>
    leftDay.date.localeCompare(rightDay.date),
  );
  const weekCount =
    orderedDays.reduce(
      (maxWeekIndex, day) => Math.max(maxWeekIndex, day.weekIndex),
      0,
    ) + 1;

  return (
    <section
      ref={ref}
      className="grid scroll-mt-6 grid-cols-[44px_minmax(0,1fr)] gap-4"
      aria-label={`Year ${year}`}
    >
      <div className="flex items-center justify-center">
        <span className="-rotate-90 text-[11px] font-semibold uppercase tracking-[0.4em] text-slate-500">
          {year}
        </span>
      </div>
      <div className="rounded-[22px] border border-white/70 bg-white/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
        <div
          className="grid grid-rows-7 justify-start gap-1"
          style={{ gridTemplateColumns: `repeat(${weekCount}, max-content)` }}
        >
          {orderedDays.map((day) => (
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
});
