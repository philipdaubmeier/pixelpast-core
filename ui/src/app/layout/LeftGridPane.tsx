import { useState } from "react";
import { YearGridStack } from "../../features/timeline/components/YearGridStack";
import type { HeatmapDayRenderProjection } from "../../projections/exploration";
import type { DateRange } from "../../projections/timeline";

type LeftGridPaneProps = {
  days: HeatmapDayRenderProjection[];
  viewColorToken: string;
  hoveredDate: string | null;
  onVisibleRangesChange: (ranges: DateRange[]) => void;
  onHover: (date: string | null) => void;
};

export function LeftGridPane({
  days,
  viewColorToken,
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
      <div
        ref={setScrollContainer}
        className="thin-scrollbar min-h-0 flex-1 overflow-y-auto pr-2"
        onMouseLeave={() => onHover(null)}
      >
        <YearGridStack
          days={days}
          viewColorToken={viewColorToken}
          hoveredDate={hoveredDate}
          scrollRoot={scrollContainer}
          onVisibleRangesChange={onVisibleRangesChange}
          onHover={onHover}
        />
      </div>
    </section>
  );
}
