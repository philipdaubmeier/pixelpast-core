import { useEffect, useRef } from "react";
import type { HeatmapDayRenderProjection } from "../../../projections/exploration";
import type { DateRange } from "../../../projections/timeline";
import type { ViewMode } from "../../../state/ui-state";
import { YearGrid } from "./YearGrid";

type YearGridStackProps = {
  days: HeatmapDayRenderProjection[];
  viewMode: ViewMode;
  hoveredDate: string | null;
  scrollRoot: HTMLDivElement | null;
  onVisibleRangesChange: (ranges: DateRange[]) => void;
  onHover: (date: string | null) => void;
};

export function YearGridStack({
  days,
  viewMode,
  hoveredDate,
  scrollRoot,
  onVisibleRangesChange,
  onHover,
}: YearGridStackProps) {
  const yearRefs = useRef<Record<number, HTMLElement | null>>({});
  const hasInitializedViewport = useRef(false);
  const visibleYearsRef = useRef<Map<number, boolean>>(new Map());
  const groupedYears = days.reduce<Map<number, HeatmapDayRenderProjection[]>>(
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
  const yearRanges = new Map<number, DateRange>(
    orderedYears.map((year) => {
      const yearDays = [...(groupedYears.get(year) ?? [])].sort((leftDay, rightDay) =>
        leftDay.date.localeCompare(rightDay.date),
      );

      return [
        year,
        {
          start: yearDays[0]?.date ?? `${year}-01-01`,
          end: yearDays[yearDays.length - 1]?.date ?? `${year}-12-31`,
        },
      ];
    }),
  );

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

  useEffect(() => {
    if (scrollRoot === null || orderedYears.length === 0) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const yearValue = entry.target.getAttribute("data-year");

          if (yearValue === null) {
            continue;
          }

          visibleYearsRef.current.set(
            Number(yearValue),
            entry.isIntersecting,
          );
        }

        const nextRanges = orderedYears
          .filter((year) => visibleYearsRef.current.get(year) ?? false)
          .map((year) => yearRanges.get(year))
          .filter((range): range is DateRange => range !== undefined);

        onVisibleRangesChange(nextRanges);
      },
      {
        root: scrollRoot,
        threshold: 0,
      },
    );

    for (const year of orderedYears) {
      const node = yearRefs.current[year];

      if (node !== null && node !== undefined) {
        observer.observe(node);
      }
    }

    return () => observer.disconnect();
  }, [onVisibleRangesChange, orderedYears, orderedYearsKey, scrollRoot, yearRanges]);

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
