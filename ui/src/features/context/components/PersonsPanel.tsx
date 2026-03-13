import { PanelCard } from "../../../components/PanelCard";
import { Pill } from "../../../components/Pill";
import type { PersonPanelItemProjection } from "../../../projections/exploration";

type HoverContextStatus = "idle" | "loading" | "ready" | "error";

type PersonsPanelProps = {
  persons: PersonPanelItemProjection[];
  hoveredDate: string | null;
  hoverContextStatus: HoverContextStatus;
  hoverContextError: string | null;
  onTogglePerson: (personId: string) => void;
};

export function PersonsPanel({
  persons,
  hoveredDate,
  hoverContextStatus,
  hoverContextError,
  onTogglePerson,
}: PersonsPanelProps) {
  const hasPersons = persons.length > 0;

  return (
    <PanelCard title="Persons">
      {hoveredDate !== null && hoverContextStatus !== "ready" ? (
        <div
          className={[
            "mb-3 rounded-2xl border px-3 py-2 text-sm",
            hoverContextStatus === "error"
              ? "border-rose-200 bg-rose-50 text-rose-700"
              : "border-amber-200 bg-amber-50 text-amber-700",
          ].join(" ")}
        >
          {hoverContextStatus === "error"
            ? hoverContextError ?? "Unable to load person context for this day."
            : `Loading person context for ${hoveredDate}.`}
        </div>
      ) : null}
      {hasPersons ? (
        <div className="thin-scrollbar -m-1 flex h-full content-start flex-wrap gap-2 overflow-y-auto p-2 pr-3">
          {persons.map((person) => (
            <Pill
              key={person.id}
              active={person.isSelected}
              hoverHighlighted={person.isHoverHighlighted}
              onClick={() => onTogglePerson(person.id)}
            >
              {person.name}
            </Pill>
          ))}
        </div>
      ) : (
        <div className="flex h-full min-h-32 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          {hoveredDate && hoverContextStatus === "loading"
            ? "Loading people linked to this day."
            : hoveredDate && hoverContextStatus === "error"
              ? "Person context could not be loaded for this day."
            : hoveredDate
            ? "No person context is attached to this day."
            : "No persons in the current context."}
        </div>
      )}
    </PanelCard>
  );
}
