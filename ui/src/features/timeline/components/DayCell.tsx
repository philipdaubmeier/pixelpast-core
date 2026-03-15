import type { HeatmapDayRenderProjection } from "../../../projections/exploration";

type DayCellProps = {
  day: HeatmapDayRenderProjection;
  viewColorToken: string;
  isHovered: boolean;
  onHover: (date: string | null) => void;
};

const emptyTone = {
  backgroundColor: "var(--pp-grid-muted)",
  opacity: 0.45,
};

function getTone(
  colorValue: HeatmapDayRenderProjection["colorValue"],
  viewColorToken: string,
) {
  if (colorValue === "empty") {
    return emptyTone;
  }

  if (colorValue === "low") {
    return { backgroundColor: viewColorToken, opacity: 0.45 };
  }

  if (colorValue === "medium") {
    return { backgroundColor: viewColorToken, opacity: 0.7 };
  }

  return { backgroundColor: viewColorToken, opacity: 1 };
}

export function DayCell({ day, viewColorToken, isHovered, onHover }: DayCellProps) {
  const tone = getTone(day.renderColorValue, viewColorToken);
  const opacity = day.isDimmed ? Math.max(0.16, tone.opacity * 0.26) : tone.opacity;
  const title = [
    day.date,
    `${day.count} items`,
    day.hasPersistentFilters
      ? day.matchesPersistentFilters
        ? "matches persistent filters"
        : "outside current filters"
      : "no persistent filters",
  ].join(" - ");

  return (
    <button
      type="button"
      onMouseEnter={() => onHover(day.date)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(day.date)}
      onBlur={() => onHover(null)}
      className={[
        "h-3.5 w-3.5 rounded-[4px] border transition duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/55 focus-visible:ring-offset-1",
        day.hasData
          ? "border-white/50 shadow-[0_1px_0_rgba(255,255,255,0.45)]"
          : "border-[color:rgba(98,80,46,0.14)]",
        isHovered
          ? "scale-110 ring-2 ring-slate-900/55 ring-offset-1"
          : "hover:scale-105 hover:border-slate-800/20",
      ].join(" ")}
      style={{
        backgroundColor: tone.backgroundColor,
        opacity,
        gridColumnStart: day.weekIndex + 1,
        gridRowStart: day.weekdayIndex + 1,
      }}
      aria-label={day.date}
      title={title}
    />
  );
}
