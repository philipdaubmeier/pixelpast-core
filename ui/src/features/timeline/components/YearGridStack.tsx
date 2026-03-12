import { useEffect, useRef } from "react";
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
  const yearRefs = useRef<Record<number, HTMLElement | null>>({});
  const hasInitializedViewport = useRef(false);
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

  const orderedYears = Array.from(groupedYears.keys()).sort(
    (leftYear, rightYear) => leftYear - rightYear,
  );
  const orderedYearsKey = orderedYears.join(",");

  useEffect(() => {
    if (hasInitializedViewport.current || orderedYears.length === 0) {
      return;
    }

    const currentYear = new Date().getFullYear();
    const initialYear = orderedYears.includes(currentYear)
      ? currentYear
      : orderedYears[orderedYears.length - 1];
    const target = yearRefs.current[initialYear];

    if (target !== undefined && target !== null) {
      target.scrollIntoView({ block: "start", behavior: "auto" });
      hasInitializedViewport.current = true;
    }
  }, [orderedYears, orderedYearsKey]);

  return (
    <div className="space-y-7">
      {orderedYears.map((year) => (
        <YearGrid
          key={year}
          ref={(node) => {
            yearRefs.current[year] = node;
          }}
          year={year}
          days={groupedYears.get(year) ?? []}
          viewMode={viewMode}
          hoveredDate={hoveredDate}
          onHover={onHover}
        />
      ))}
    </div>
  );
}
