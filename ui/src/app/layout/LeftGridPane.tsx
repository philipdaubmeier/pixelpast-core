import { YearGridStack } from "../../features/timeline/components/YearGridStack";
import type { HeatmapDayProjection } from "../../projections/timeline";
import type { ViewMode } from "../../state/ui-state";

type LeftGridPaneProps = {
  days: HeatmapDayProjection[];
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
  return (
    <section className="panel-surface min-h-[42rem] overflow-hidden p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="panel-title">Timeline Grid</p>
          <h2 className="text-xl font-semibold text-slate-950">
            Year stack placeholder
          </h2>
        </div>
        <p className="panel-copy">Oldest year first, current year last.</p>
      </div>
      <div className="h-[calc(100vh-17rem)] min-h-[32rem] overflow-y-auto pr-2">
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
