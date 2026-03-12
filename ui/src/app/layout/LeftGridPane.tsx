import { YearGridStack } from "../../features/timeline/components/YearGridStack";
import type { HeatmapDayRenderProjection } from "../../projections/exploration";
import type { ViewMode } from "../../state/ui-state";

type LeftGridPaneProps = {
  days: HeatmapDayRenderProjection[];
  viewMode: ViewMode;
  hoveredDate: string | null;
  onHover: (date: string | null) => void;
};

export function LeftGridPane({
  days,
  viewMode,
  hoveredDate,
  onHover,
}: LeftGridPaneProps) {
  const years = Array.from(new Set(days.map((day) => day.year))).sort(
    (leftYear, rightYear) => leftYear - rightYear,
  );
  const yearRangeLabel =
    years.length > 1
      ? `${years[0]} to ${years[years.length - 1]}`
      : years[0]?.toString() ?? "Timeline";

  return (
    <section className="panel-surface min-h-[42rem] overflow-hidden p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="panel-title">Timeline Grid</p>
          <h2 className="text-xl font-semibold text-slate-950">
            {yearRangeLabel}
          </h2>
        </div>
        <p className="panel-copy">
          Oldest year first, current year auto-focused, persistent filters recolor
          the grid.
        </p>
      </div>
      <div
        className="h-[calc(100vh-17rem)] min-h-[32rem] overflow-y-auto pr-2"
        onMouseLeave={() => onHover(null)}
      >
        <YearGridStack
          days={days}
          viewMode={viewMode}
          hoveredDate={hoveredDate}
          onHover={onHover}
        />
      </div>
    </section>
  );
}
