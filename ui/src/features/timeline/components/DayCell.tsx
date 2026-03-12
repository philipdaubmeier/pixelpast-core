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
      className={[
        "h-3.5 w-3.5 rounded-[4px] border border-white/40 transition",
        isHovered
          ? "scale-110 ring-2 ring-slate-900/55 ring-offset-1"
          : "hover:scale-105",
      ].join(" ")}
      style={tone}
      aria-label={day.date}
      title={`${day.date} · ${day.eventCount} events · ${day.assetCount} assets`}
    />
  );
}
