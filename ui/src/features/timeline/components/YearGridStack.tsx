import { memo, useEffect, useMemo, useRef } from "react";
import type { HeatmapDayRenderProjection } from "../../../projections/exploration";
import type { DateRange } from "../../../projections/timeline";
import { YearGrid } from "./YearGrid";

type YearGridStackProps = {
  days: HeatmapDayRenderProjection[];
  viewColorToken: string;
  scrollRoot: HTMLDivElement | null;
  onVisibleRangesChange: (ranges: DateRange[]) => void;
  onHover: (date: string | null) => void;
};

type YearEntry = {
  year: number;
  days: HeatmapDayRenderProjection[];
  range: DateRange;
};

export const YearGridStack = memo(function YearGridStack({
  days,
  viewColorToken,
  scrollRoot,
  onVisibleRangesChange,
  onHover,
}: YearGridStackProps) {
  const yearRefs = useRef<Record<number, HTMLElement | null>>({});
  const hasInitializedViewport = useRef(false);
  const visibleYearsRef = useRef<Map<number, boolean>>(new Map());
  const yearEntries = useMemo<YearEntry[]>(() => {
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

    return Array.from(groupedYears.entries())
      .sort(([leftYear], [rightYear]) => leftYear - rightYear)
      .map(([year, yearDays]) => {
        const orderedDays = [...yearDays].sort((leftDay, rightDay) =>
          leftDay.date.localeCompare(rightDay.date),
        );

        return {
          year,
          days: orderedDays,
          range: {
            start: orderedDays[0]?.date ?? `${year}-01-01`,
            end: orderedDays[orderedDays.length - 1]?.date ?? `${year}-12-31`,
          },
        };
      });
  }, [days]);
  const orderedYears = useMemo(
    () => yearEntries.map((entry) => entry.year),
    [yearEntries],
  );
  const orderedYearsKey = orderedYears.join(",");
  const yearRanges = useMemo(
    () => new Map(yearEntries.map((entry) => [entry.year, entry.range])),
    [yearEntries],
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
    <div className="space-y-[0.9rem]">
      {yearEntries.map((entry) => (
        <YearGrid
          key={entry.year}
          ref={(node) => {
            yearRefs.current[entry.year] = node;
          }}
          year={entry.year}
          days={entry.days}
          viewColorToken={viewColorToken}
          onHover={onHover}
        />
      ))}
    </div>
  );
});
