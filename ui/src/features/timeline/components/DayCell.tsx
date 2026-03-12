import type { HeatmapDayProjection } from "../../../projections/timeline";
import type { ViewMode } from "../../../state/ui-state";

type DayCellProps = {
  day: HeatmapDayProjection;
  viewMode: ViewMode;
  isHovered: boolean;
  onHover: (date: string | null) => void;
};

const toneByViewMode: Record<
  ViewMode,
  Record<
    HeatmapDayProjection["colorValue"],
    { backgroundColor: string; opacity: number }
  >
> = {
  activity: {
    empty: { backgroundColor: "var(--pp-grid-muted)", opacity: 0.45 },
    low: { backgroundColor: "var(--pp-grid-activity)", opacity: 0.45 },
    medium: { backgroundColor: "var(--pp-grid-activity)", opacity: 0.7 },
    high: { backgroundColor: "var(--pp-grid-activity)", opacity: 1 },
  },
  travel: {
    empty: { backgroundColor: "var(--pp-grid-muted)", opacity: 0.45 },
    low: { backgroundColor: "var(--pp-grid-travel)", opacity: 0.45 },
    medium: { backgroundColor: "var(--pp-grid-travel)", opacity: 0.7 },
    high: { backgroundColor: "var(--pp-grid-travel)", opacity: 1 },
  },
  sports: {
    empty: { backgroundColor: "var(--pp-grid-muted)", opacity: 0.45 },
    low: { backgroundColor: "var(--pp-grid-sports)", opacity: 0.45 },
    medium: { backgroundColor: "var(--pp-grid-sports)", opacity: 0.7 },
    high: { backgroundColor: "var(--pp-grid-sports)", opacity: 1 },
  },
  party_probability: {
    empty: { backgroundColor: "var(--pp-grid-muted)", opacity: 0.45 },
    low: { backgroundColor: "var(--pp-grid-party)", opacity: 0.45 },
    medium: { backgroundColor: "var(--pp-grid-party)", opacity: 0.7 },
    high: { backgroundColor: "var(--pp-grid-party)", opacity: 1 },
  },
};

export function DayCell({ day, viewMode, isHovered, onHover }: DayCellProps) {
  const tone = toneByViewMode[viewMode][day.colorValue];

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
        ...tone,
        gridColumnStart: day.weekIndex + 1,
        gridRowStart: day.weekdayIndex + 1,
      }}
      aria-label={day.date}
      title={`${day.date} - ${day.eventCount} events - ${day.assetCount} assets`}
    />
  );
}
