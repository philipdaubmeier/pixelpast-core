import { useState } from "react";
import { YearGridStack } from "../../features/timeline/components/YearGridStack";
import type { HeatmapDayRenderProjection } from "../../projections/exploration";
import type { DateRange } from "../../projections/timeline";
import type { ViewMode } from "../../state/ui-state";

type LeftGridPaneProps = {
  days: HeatmapDayRenderProjection[];
  viewMode: ViewMode;
  hoveredDate: string | null;
  onVisibleRangesChange: (ranges: DateRange[]) => void;
  onHover: (date: string | null) => void;
};

export function LeftGridPane({
  days,
  viewMode,
  hoveredDate,
  onVisibleRangesChange,
  onHover,
}: LeftGridPaneProps) {
  const [scrollContainer, setScrollContainer] = useState<HTMLDivElement | null>(
    null,
  );
  const years = Array.from(new Set(days.map((day) => day.year))).sort(
    (leftYear, rightYear) => leftYear - rightYear,
  );
  const yearRangeLabel =
    years.length > 1
      ? `${years[0]} to ${years[years.length - 1]}`
      : years[0]?.toString() ?? "Timeline";

  return (
    <section className="panel-surface flex h-full min-h-0 flex-col overflow-hidden p-3 lg:p-3.5">
      <div className="mb-3 flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-slate-950">{yearRangeLabel}</h2>
      </div>
      <div
        ref={setScrollContainer}
        className="thin-scrollbar min-h-0 flex-1 overflow-y-auto pr-2"
        onMouseLeave={() => onHover(null)}
      >
        <YearGridStack
          days={days}
          viewMode={viewMode}
          hoveredDate={hoveredDate}
          scrollRoot={scrollContainer}
          onVisibleRangesChange={onVisibleRangesChange}
          onHover={onHover}
        />
      </div>
    </section>
  );
}
