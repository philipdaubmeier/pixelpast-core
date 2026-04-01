import { PanelCard } from "../../../components/PanelCard";
import type { MapPointProjection } from "../../../projections/timeline";

type HoverContextStatus = "idle" | "loading" | "ready" | "error";

type MapPanelProps = {
  contextLabel: string | null;
  mapPoints: MapPointProjection[];
  highlightedPointIds?: string[];
  hasPersistentFilters: boolean;
  contextStatus: HoverContextStatus;
  contextError: string | null;
  loadingMessage?: string;
  errorMessage?: string;
  emptySelectionMessage?: string;
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
  contextLabel,
  mapPoints,
  highlightedPointIds = [],
  hasPersistentFilters,
  contextStatus,
  contextError,
  loadingMessage,
  errorMessage,
  emptySelectionMessage,
  summary,
}: MapPanelProps) {
  const highlightedPointIdSet = new Set(highlightedPointIds);
  const labeledPoints = mapPoints.filter((point) => point.label !== null);
  const unlabeledPoints = mapPoints.filter((point) => point.label === null);
  const pathPolylinePoints = unlabeledPoints
    .map(
      (point) =>
        `${projectLongitude(point.longitude)},${projectLatitude(point.latitude)}`,
    )
    .join(" ");

  return (
    <PanelCard title="Map">
      {contextLabel !== null && contextStatus !== "ready" ? (
        <div
          className={[
            "mb-3 rounded-2xl border px-3 py-2 text-sm",
            contextStatus === "error"
              ? "border-rose-200 bg-rose-50 text-rose-700"
              : "border-amber-200 bg-amber-50 text-amber-700",
          ].join(" ")}
        >
          {contextStatus === "error"
            ? contextError ?? errorMessage ?? "Unable to load map context."
            : loadingMessage ?? `Loading map context for ${contextLabel}.`}
        </div>
      ) : null}
      <div className="subtle-grid relative min-h-[10rem] overflow-hidden rounded-[22px] border border-white/70 bg-stone-100/70">
        {mapPoints.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-slate-500">
            {contextLabel && contextStatus === "loading"
              ? loadingMessage ?? "Preparing coordinates for this selection."
              : contextLabel && contextStatus === "error"
                ? errorMessage ?? "Map context failed to load."
              : contextLabel
              ? emptySelectionMessage ?? "No coordinates in the current selection."
                : hasPersistentFilters
              ? "No coordinates matched the current persistent filters."
              : "No location context."}
          </div>
        ) : (
          <>
            {unlabeledPoints.length > 0 ? (
              <svg
                className="pointer-events-none absolute inset-0 h-full w-full"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                {unlabeledPoints.length >= 2 ? (
                  <polyline
                    points={pathPolylinePoints}
                    fill="none"
                    stroke="rgba(15, 23, 42, 0.85)"
                    strokeWidth="0.9"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                ) : null}
                {unlabeledPoints.map((point, index) => (
                  <circle
                    key={`path-point-${point.id ?? index}`}
                    cx={projectLongitude(point.longitude)}
                    cy={projectLatitude(point.latitude)}
                    r={
                      highlightedPointIdSet.has(point.id ?? "")
                        ? 1.75
                        : unlabeledPoints.length >= 2
                          ? 0.55
                          : 1.2
                    }
                    fill={
                      highlightedPointIdSet.has(point.id ?? "")
                        ? "rgba(217, 119, 6, 0.95)"
                        : "rgba(15, 23, 42, 0.88)"
                    }
                  />
                ))}
              </svg>
            ) : null}
            {labeledPoints.map((point, index) => (
              <div
                key={point.id ?? `labeled-point-${index}`}
                className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1"
                style={{
                  left: `${projectLongitude(point.longitude)}%`,
                  top: `${projectLatitude(point.latitude)}%`,
                }}
              >
                <span
                  className={[
                    "h-3.5 w-3.5 rounded-full shadow-[0_0_0_4px_rgba(255,255,255,0.65)]",
                    highlightedPointIdSet.has(point.id ?? "")
                      ? "bg-amber-600"
                      : "bg-slate-900",
                  ].join(" ")}
                />
                <span className="rounded-full bg-white/85 px-2 py-1 text-[11px] font-medium text-slate-700">
                  {point.label}
                </span>
              </div>
            ))}
          </>
        )}
        <div className="pointer-events-none absolute inset-x-3 bottom-3 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-2xl bg-[color:rgba(255,252,247,0.9)] px-2 py-2 shadow-[0_8px_24px_rgba(61,44,15,0.08)] backdrop-blur-sm">
            <div className="text-base font-semibold text-slate-900">
              {summary?.events ?? 0}
            </div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
              Events
            </div>
          </div>
          <div className="rounded-2xl bg-[color:rgba(255,252,247,0.9)] px-2 py-2 shadow-[0_8px_24px_rgba(61,44,15,0.08)] backdrop-blur-sm">
            <div className="text-base font-semibold text-slate-900">
              {summary?.assets ?? 0}
            </div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
              Assets
            </div>
          </div>
          <div className="rounded-2xl bg-[color:rgba(255,252,247,0.9)] px-2 py-2 shadow-[0_8px_24px_rgba(61,44,15,0.08)] backdrop-blur-sm">
            <div className="text-base font-semibold text-slate-900">
              {summary?.places ?? 0}
            </div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
              Places
            </div>
          </div>
        </div>
      </div>
    </PanelCard>
  );
}
