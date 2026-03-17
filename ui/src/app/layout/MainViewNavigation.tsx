import type { MainView } from "../../state/ui-state";

type MainViewNavigationProps = {
  activeMainView: MainView;
  onSelect: (mainView: MainView) => void;
};

export function MainViewNavigation({
  activeMainView,
  onSelect,
}: MainViewNavigationProps) {
  return (
    <nav
      aria-label="Main views"
      className="flex items-center gap-2 rounded-full border border-[color:var(--pp-border)] bg-white/65 px-2 py-1 shadow-[0_10px_24px_rgba(61,44,15,0.05)]"
    >
      <span className="px-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
        Main view
      </span>
      <button
        type="button"
        onClick={() => onSelect("day_grid")}
        aria-current={activeMainView === "day_grid" ? "page" : undefined}
        className={[
          "rounded-full px-3 py-1.5 text-[12px] font-medium transition",
          activeMainView === "day_grid"
            ? "bg-slate-900 text-white shadow-[0_10px_28px_rgba(15,23,42,0.16)]"
            : "bg-transparent text-slate-700 hover:bg-white",
        ].join(" ")}
      >
        Day Grid
      </button>
      <button
        type="button"
        onClick={() => onSelect("social_graph")}
        aria-current={activeMainView === "social_graph" ? "page" : undefined}
        className={[
          "rounded-full px-3 py-1.5 text-[12px] font-medium transition",
          activeMainView === "social_graph"
            ? "bg-slate-900 text-white shadow-[0_10px_28px_rgba(15,23,42,0.16)]"
            : "bg-transparent text-slate-700 hover:bg-white",
        ].join(" ")}
      >
        Social Graph
      </button>
    </nav>
  );
}
