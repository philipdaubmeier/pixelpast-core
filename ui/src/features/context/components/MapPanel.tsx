import { PanelCard } from "../../../components/PanelCard";
import type { MapPointProjection } from "../../../projections/timeline";

type HoverContextStatus = "idle" | "loading" | "ready" | "error";

type MapPanelProps = {
  hoveredDate: string | null;
  mapPoints: MapPointProjection[];
  hasPersistentFilters: boolean;
  hoverContextStatus: HoverContextStatus;
  hoverContextError: string | null;
  summary: {
    events: number;
    assets: number;
    places: number;
  } | null;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function projectLongitude(longitude: number): number {
  return clamp(((longitude + 180) / 360) * 100, 8, 92);
}

function projectLatitude(latitude: number): number {
  return clamp(((90 - latitude) / 180) * 100, 10, 90);
}

export function MapPanel({
  hoveredDate,
  mapPoints,
  hasPersistentFilters,
  hoverContextStatus,
  hoverContextError,
  summary,
}: MapPanelProps) {
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
      {hoveredDate !== null && hoverContextStatus !== "ready" ? (
        <div
          className={[
            "mb-4 rounded-2xl border px-3 py-2 text-sm",
            hoverContextStatus === "error"
              ? "border-rose-200 bg-rose-50 text-rose-700"
              : "border-amber-200 bg-amber-50 text-amber-700",
          ].join(" ")}
        >
          {hoverContextStatus === "error"
            ? hoverContextError ?? "Unable to load hover context for this day."
            : `Loading hover context for ${hoveredDate}.`}
        </div>
      ) : null}
      <div className="subtle-grid relative min-h-[10rem] overflow-hidden rounded-[22px] border border-white/70 bg-stone-100/70">
        {mapPoints.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-slate-500">
            {hoveredDate && hoverContextStatus === "loading"
              ? "Preparing coordinates for the hovered day."
              : hoveredDate && hoverContextStatus === "error"
                ? "Hover context failed to load for this day."
                : hasPersistentFilters
              ? "No coordinates matched the current persistent filters."
              : "Hover a day to project its coordinates here."}
          </div>
        ) : (
          <>
            {mapPoints.map((point) => (
              <div
                key={point.id}
                className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1"
                style={{
                  left: `${projectLongitude(point.longitude)}%`,
                  top: `${projectLatitude(point.latitude)}%`,
                }}
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
