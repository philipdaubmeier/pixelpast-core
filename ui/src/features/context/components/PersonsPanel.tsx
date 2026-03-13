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
    <PanelCard
      eyebrow="Context"
      title="Persons"
      description={
        hoveredDate
          ? `Reacting to ${hoveredDate} while keeping persistent person filters visible.`
          : "Hover a day to preview its people, or pin people as durable filters."
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
            ? hoverContextError ?? "Unable to load person context for this day."
            : `Loading person context for ${hoveredDate}.`}
        </div>
      ) : null}
      {hasPersons ? (
        <>
          <div className="flex flex-wrap gap-2">
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
          <div className="mt-4 space-y-2">
            {persons.map((person) => (
              <div
                key={`${person.id}-meta`}
                className={[
                  "flex items-center justify-between rounded-2xl border px-3 py-2 text-sm transition",
                  person.isSelected
                    ? "border-slate-900/15 bg-slate-900/5"
                    : "border-transparent bg-white/60",
                  person.isHoverHighlighted
                    ? "ring-2 ring-amber-400/60 ring-offset-2 ring-offset-[color:rgba(250,247,240,0.9)]"
                    : "",
                ].join(" ")}
              >
                <span className="font-medium text-slate-800">{person.name}</span>
                <span className="text-slate-500">{person.role}</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex h-full min-h-32 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          {hoveredDate && hoverContextStatus === "loading"
            ? "Loading people linked to this day."
            : hoveredDate && hoverContextStatus === "error"
              ? "Person context could not be loaded for this day."
              : hoveredDate
            ? "No person context is attached to this day."
            : "Hover a day to inspect its people. Selected person filters will stay active independently."}
        </div>
      )}
    </PanelCard>
  );
}
