import type { HeatmapDayProjection } from "../../../projections/timeline";
import type { ViewMode } from "../../../state/ui-state";
import { YearGrid } from "./YearGrid";

type YearGridStackProps = {
  days: HeatmapDayProjection[];
  viewMode: ViewMode;
  hoveredDate: string | null;
  onHover: (date: string | null) => void;
};

export function YearGridStack({
  days,
  viewMode,
  hoveredDate,
  onHover,
}: YearGridStackProps) {
  const groupedYears = days.reduce<Map<number, HeatmapDayProjection[]>>(
    (accumulator, day) => {
      const entry = accumulator.get(day.year);

      if (entry) {
        entry.push(day);
      } else {
        accumulator.set(day.year, [day]);
      }

      return accumulator;
    },
    new Map(),
  );

  const orderedYears = Array.from(groupedYears.entries()).sort(
    ([leftYear], [rightYear]) => leftYear - rightYear,
  );

  return (
    <div className="space-y-7">
      {orderedYears.map(([year, yearDays]) => (
        <YearGrid
          key={year}
          year={year}
          days={yearDays}
          viewMode={viewMode}
          hoveredDate={hoveredDate}
          onHover={onHover}
        />
      ))}
    </div>
  );
}
