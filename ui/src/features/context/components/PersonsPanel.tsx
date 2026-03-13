import { PanelCard } from "../../../components/PanelCard";
import { Pill } from "../../../components/Pill";
import type { PersonPanelItemProjection } from "../../../projections/exploration";

type PersonsPanelProps = {
  persons: PersonPanelItemProjection[];
  hoveredDate: string | null;
  onTogglePerson: (personId: string) => void;
};

export function PersonsPanel({
  persons,
  hoveredDate,
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
          {hoveredDate
            ? "No person context is attached to this day."
            : "Hover a day to inspect its people. Selected person filters will stay active independently."}
        </div>
      )}
    </PanelCard>
  );
}
