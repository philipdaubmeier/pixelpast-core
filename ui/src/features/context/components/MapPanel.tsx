import { PanelCard } from "../../../components/PanelCard";
import type { MapPointProjection } from "../../../projections/timeline";

type MapPanelProps = {
  hoveredDate: string | null;
  mapPoints: MapPointProjection[];
  summary: {
    events: number;
    assets: number;
    places: number;
  } | null;
};

export function MapPanel({ hoveredDate, mapPoints, summary }: MapPanelProps) {
  return (
    <PanelCard
      eyebrow="Context"
      title="Map"
      description={
        hoveredDate
          ? `Subtle spatial context for ${hoveredDate}. The map supports the grid, it does not replace it.`
          : "A quiet map surface reserved for hovered-day and filtered-location context."
      }
    >
      <div className="subtle-grid relative min-h-[10rem] overflow-hidden rounded-[22px] border border-white/70 bg-stone-100/70">
        {mapPoints.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-slate-500">
            Hover a day to project its coordinates here.
          </div>
        ) : (
          <>
            {mapPoints.map((point) => (
              <div
                key={point.id}
                className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1"
                style={{ left: `${point.x}%`, top: `${point.y}%` }}
              >
                <span className="h-3.5 w-3.5 rounded-full bg-slate-900 shadow-[0_0_0_4px_rgba(255,255,255,0.65)]" />
                <span className="rounded-full bg-white/85 px-2 py-1 text-[11px] font-medium text-slate-700">
                  {point.label}
                </span>
              </div>
            ))}
          </>
        )}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3 text-center">
        <div className="rounded-2xl bg-white/60 px-3 py-3">
          <div className="text-lg font-semibold text-slate-900">
            {summary?.events ?? 0}
          </div>
          <div className="text-xs uppercase tracking-[0.22em] text-slate-500">
            Events
          </div>
        </div>
        <div className="rounded-2xl bg-white/60 px-3 py-3">
          <div className="text-lg font-semibold text-slate-900">
            {summary?.assets ?? 0}
          </div>
          <div className="text-xs uppercase tracking-[0.22em] text-slate-500">
            Assets
          </div>
        </div>
        <div className="rounded-2xl bg-white/60 px-3 py-3">
          <div className="text-lg font-semibold text-slate-900">
            {summary?.places ?? 0}
          </div>
          <div className="text-xs uppercase tracking-[0.22em] text-slate-500">
            Places
          </div>
        </div>
      </div>
    </PanelCard>
  );
}
