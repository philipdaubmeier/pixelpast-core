import logoUrl from "../../assets/pixelpast-logo.svg";
import type { PersonGroupProjection } from "../../api/personGroups";
import { FilterBar } from "../../features/timeline/components/FilterBar";
import { GridViewSelector } from "../../features/timeline/components/GridViewSelector";
import type {
  GridViewOption,
  PersonProjection,
  TagProjection,
} from "../../projections/timeline";
import type { GridView, MainView } from "../../state/ui-state";
import { MainViewNavigation } from "./MainViewNavigation";
import { PersonGroupFilterControl } from "./PersonGroupFilterControl";

type TopBarProps = {
  mainView: MainView;
  gridViews: GridViewOption[];
  activeGridView: GridView;
  activeGridViewLabel: string;
  selectedPersons: PersonProjection[];
  selectedPersonGroups: PersonGroupProjection[];
  selectedTags: TagProjection[];
  personGroups: PersonGroupProjection[];
  personGroupCatalogState: "loading" | "ready" | "error";
  personGroupCatalogError: string | null;
  transportState: "loading" | "ready" | "error";
  transportError: string | null;
  onSelectMainView: (mainView: MainView) => void;
  onSelectGridView: (gridView: GridView) => void;
  onTogglePerson: (personId: string) => void;
  onTogglePersonGroup: (groupId: string) => void;
  onToggleTag: (tagPath: string) => void;
  onClearSelections: () => void;
  isManageDataOpen: boolean;
  onToggleManageData: () => void;
};

export function TopBar({
  mainView,
  gridViews,
  activeGridView,
  activeGridViewLabel,
  selectedPersons,
  selectedPersonGroups,
  selectedTags,
  personGroups,
  personGroupCatalogState,
  personGroupCatalogError,
  transportState,
  transportError,
  onSelectMainView,
  onSelectGridView,
  onTogglePerson,
  onTogglePersonGroup,
  onToggleTag,
  onClearSelections,
  isManageDataOpen,
  onToggleManageData,
}: TopBarProps) {
  return (
    <header className="thin-scrollbar fixed inset-x-0 top-0 z-30 overflow-x-auto border-b border-[color:var(--pp-border)] bg-[color:rgba(255,249,241,0.96)] shadow-[0_10px_30px_rgba(61,44,15,0.06)] backdrop-blur-sm">
      <div className="min-w-max px-4 py-2 lg:px-5">
        <div className="flex min-h-[4rem] items-center gap-4">
          <img
            src={logoUrl}
            alt="PixelPast"
            className="h-12 w-auto shrink-0 lg:h-[3.35rem]"
          />
          <div className="flex min-w-max items-center gap-3 lg:gap-4">
            <MainViewNavigation
              activeMainView={mainView}
              onSelect={onSelectMainView}
            />
            <PersonGroupFilterControl
              groups={personGroups}
              selectedGroupIds={selectedPersonGroups.map((group) => group.id)}
              state={personGroupCatalogState}
              error={personGroupCatalogError}
              onToggleGroup={onTogglePersonGroup}
              onClear={onClearSelections}
            />
            <FilterBar
              selectedPersons={selectedPersons}
              selectedPersonGroups={selectedPersonGroups}
              selectedTags={selectedTags}
              onRemovePerson={onTogglePerson}
              onRemovePersonGroup={onTogglePersonGroup}
              onRemoveTag={onToggleTag}
            />
          </div>
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
              {transportState === "loading"
                ? "Data: updating"
                : transportState === "error"
                  ? transportError ?? "Data: request failed"
                  : "Data: synced"}
            </div>
            <button
              type="button"
              onClick={onToggleManageData}
              aria-pressed={isManageDataOpen}
              className={[
                "rounded-full border px-4 py-2 text-sm font-medium transition",
                isManageDataOpen
                  ? "border-slate-900 bg-slate-900 text-white shadow-[0_12px_28px_rgba(15,23,42,0.16)]"
                  : "border-[color:rgba(98,80,46,0.2)] bg-white/55 text-slate-600 hover:bg-white/85",
              ].join(" ")}
            >
              Manage
            </button>
          </div>
        </div>
        {mainView === "day_grid" ? (
          <div className="flex min-h-[2.5rem] items-center pl-[4.4rem] lg:pl-[5rem]">
            <div className="flex items-center gap-3 rounded-full bg-[color:rgba(255,255,255,0.45)] px-3 py-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Day Grid
              </span>
              <GridViewSelector
                options={gridViews}
                activeGridView={activeGridView}
                onSelect={onSelectGridView}
              />
            </div>
          </div>
        ) : null}
      </div>
    </header>
  );
}
