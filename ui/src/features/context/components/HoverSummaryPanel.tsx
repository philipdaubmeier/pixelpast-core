type HoverSummaryPanelProps = {
  summary: {
    events: number;
    assets: number;
    places: number;
  } | null;
};

const summaryItems = [
  { key: "events", label: "Events" },
  { key: "assets", label: "Assets" },
  { key: "places", label: "Places" },
] as const;

export function HoverSummaryPanel({ summary }: HoverSummaryPanelProps) {
  return (
    <section className="panel-surface-strong flex h-fit min-h-0 flex-col self-start p-3 lg:p-3.5">
      <div className="grid grid-cols-3 gap-2">
        {summaryItems.map((item) => (
          <div
            key={item.key}
            className="rounded-2xl bg-[color:rgba(255,252,247,0.92)] px-2 py-2 text-center shadow-[0_8px_24px_rgba(61,44,15,0.08)]"
          >
            <div className="text-base font-semibold text-slate-900">
              {summary?.[item.key] ?? 0}
            </div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
              {item.label}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
